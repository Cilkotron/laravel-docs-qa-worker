# Laravel Docs Q&A

A production-grade RAG (Retrieval-Augmented Generation) chatbot built entirely on the Cloudflare stack. Answers questions about the Laravel PHP framework using its official documentation as the knowledge source, with cited sources.


## What it does

POST a natural-language question to `/api/ask` and receive a streamed AI answer with citations linking back to Laravel's official documentation.

```bash
curl -X POST https://{worker_url}/api/ask \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"How do I define a route in Laravel?"}' \
  -N
```

The response is streamed via Server-Sent Events, with citations referencing numbered sources in the answer text.

## Architecture

```
User question
     │
     ▼
┌─────────────────────────────────┐
│   Cloudflare Worker (Hono)      │
│                                 │
│  1. Auth check (Bearer token)   │
│  2. Embed question via AI       │
│  3. Query Vectorize (top-5)     │
│  4. Build prompt with context   │
│  5. Stream LLM response         │
└────────┬────────────────────────┘
         │
    ┌────┴─────┬──────────┐
    ▼          ▼          ▼
┌────────┐ ┌─────────┐ ┌────────┐
│Workers │ │Vectorize│ │Workers │
│  AI    │ │ (768-d) │ │  AI    │
│(BGE)   │ │ cosine  │ │(Llama) │
└────────┘ └─────────┘ └────────┘
   embed     retrieve   generate
```

Everything runs on Cloudflare's free tier. No external services (no OpenAI, no Pinecone, no third-party hosting).

## Tech stack

**Worker:**
- Cloudflare Workers (TypeScript)
- [Hono](https://hono.dev/) — lightweight edge-native web framework
- Workers AI bindings
- Vectorize bindings

**AI models (both via Workers AI):**
- Embeddings: `@cf/baai/bge-base-en-v1.5` (768 dimensions)
- LLM: `@cf/meta/llama-3.1-8b-instruct` (streaming responses)

**Knowledge base:**
- Source: [laravel/docs](https://github.com/laravel/docs) (branch `13.x`)
- 103 markdown files
- 2,366 chunks indexed in Vectorize
- ~500 words per chunk with 50-word overlap

**Ingest pipeline (local, Python):**
- `sentence-transformers` for local embedding generation
- `markdown-it-py` for parsing
- `gitpython` for cloning the docs repo
- Vectors uploaded to Vectorize via Wrangler CLI

## How retrieval works

Each chunk in the knowledge base carries metadata: original file, section headings (H1/H2/H3), source URL on laravel.com. When a question comes in:

1. The question is converted to a 768-dimensional vector using the same embedding model as the indexed chunks (consistency matters — different models produce incompatible vector spaces).
2. Vectorize returns the top-5 chunks ranked by cosine similarity.
3. The retrieved chunks are formatted as numbered sources and inserted into the LLM prompt as context.
4. The LLM is instructed to answer only from the provided context and cite sources using `[Source N]` notation.
5. The LLM response is streamed back to the client. Source URLs are returned in the `X-Sources` response header.

## Why this stack

A few decisions worth noting:

**Why local embedding for ingest rather than Workers AI?**
Workers AI free tier is 10,000 neurons/day. Embedding 2,366 chunks would consume most of that budget on initial indexing alone, and re-indexing would force paid usage. Local embeddings using `sentence-transformers` are free and reproducible.

**Why the same model for query-time embedding?**
Cross-model vector compatibility is unreliable. Using `BAAI/bge-base-en-v1.5` consistently — locally for ingest, on Workers AI for queries — guarantees vectors live in the same semantic space.

**Why Hono over vanilla Workers?**
Routing, middleware, and type-safe bindings out of the box. Single-handler vanilla Workers code becomes painful past two endpoints; Hono adds ~12KB and saves significant boilerplate.

**Why cosine similarity over dot product?**
The BGE model produces normalized embeddings, so cosine and dot product are equivalent in ranking. Cosine is chosen for clarity — it's the default mental model when discussing semantic similarity.

## Project structure

```
laravel-docs-qa/
├── src/
│   ├── index.ts              # Hono app: /health, /api/ask, auth middleware
│   └── bindings/
│       └── env.ts            # Type definitions for Worker bindings
├── ingest/
│   ├── clone_docs.py         # Clone laravel/docs repo
│   ├── chunk_docs.py         # Parse markdown, chunk with metadata
│   ├── embed_chunks.py       # Generate embeddings locally
│   ├── prepare_for_vectorize.py  # Convert to Vectorize NDJSON format
│   ├── test_search.py        # Smoke test: search Vectorize from CLI
│   └── requirements.txt
├── wrangler.jsonc            # Worker config with bindings
├── package.json
└── tsconfig.json
```

## Running locally

### Prerequisites
- Node.js 20+
- Python 3.12+
- Cloudflare account with Workers AI enabled
- Wrangler authenticated (`npx wrangler login`)

### One-time setup

**Worker dependencies:**
```bash
npm install
```

**Ingest pipeline dependencies:**
```bash
cd ingest
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Build the knowledge base

```bash
# From ingest/ with venv active:
python clone_docs.py            # Clone Laravel docs (~30 seconds)
python chunk_docs.py            # Split into chunks (~3 seconds)
python embed_chunks.py          # Generate embeddings (~8 minutes on CPU)
python prepare_for_vectorize.py # Convert to Vectorize format (~2 seconds)
```

### Create Vectorize index and upload vectors

```bash
# From project root:
npx wrangler vectorize create laravel-docs --dimensions=768 --metric=cosine

npx wrangler vectorize insert laravel-docs \
  --file=ingest/vectorize_upload.ndjson \
  --batch-size=1000
```

### Set the API token

```bash
# Generate a random token
openssl rand -base64 32

# Store it as a Worker Secret
npx wrangler secret put API_TOKEN
# Paste the token when prompted

# For local dev, also create .dev.vars in project root:
echo "API_TOKEN=your-token-here" > .dev.vars
```

### Run the Worker

**Locally:**
```bash
npx wrangler dev
# Test:
curl -X POST http://localhost:8787/api/ask \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"How do I define a route?"}' \
  -N
```

**Deploy to Cloudflare:**
```bash
npx wrangler deploy
```

## API

### `GET /health`

Public endpoint. Returns Worker status. No auth required.

**Response:**
```json
{
  "status": "ok",
  "timestamp": 1747824000000
}
```

### `POST /api/ask`

Protected endpoint. Requires `Authorization: Bearer <token>` header.

**Request:**
```json
{
  "question": "How do I define a route in Laravel?"
}
```

Constraints:
- `question` is required, non-empty, max 500 characters.

**Response:** `text/event-stream` (Server-Sent Events).

Each event is a JSON chunk with a `response` field carrying the next piece of the LLM output. The stream ends with `data: [DONE]`.

Source URLs for the retrieved context are returned in the `X-Sources` response header as a JSON array.

**Error responses:**
- `400` — missing/invalid question
- `401` — missing or invalid Bearer token
- `404` — no relevant context found in knowledge base
- `500` — embedding or LLM failure

## Cost notes

At rest, the entire system runs on Cloudflare free tier:
- Workers: free (100K requests/day)
- Workers AI: 10K neurons/day (≈ 100–300 question answers)
- Vectorize: 5M stored vectors free (we use 2,366)
- D1 / KV: not currently used

For 1K queries/day in production, the bottleneck would be Workers AI neurons (~$5/month on the Workers Paid plan), not infrastructure.

## License

MIT