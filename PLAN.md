# PLAN.md — Development phases

Each phase is a single focused work session (1-2 hours). After each phase, the project must be in a working, committable state. Do not start the next phase until the current one is verified working end-to-end.

---

## Phase 1 — Project skeleton & Wrangler setup
**Estimated time:** 1 hour
**Goal:** Empty but working Worker that responds to `/health` with JSON.

### Tasks
- [ ] `npm create cloudflare@latest` — pick "Hello World Worker" + TypeScript
- [ ] Add Hono: `npm install hono`
- [ ] Set up folder structure (`/src/routes`, `/src/lib`, `/src/bindings`, `/src/durable`)
- [ ] Configure `tsconfig.json` with strict mode, `noUncheckedIndexedAccess`
- [ ] Create `/health` endpoint returning `{ status: "ok", timestamp: ... }`
- [ ] Add `.gitignore` (node_modules, .dev.vars, .wrangler)
- [ ] Initial commit
- [ ] Test locally with `wrangler dev`

### Verification
- `curl http://localhost:8787/health` returns JSON 200
- TypeScript compiles with zero errors
- Repo on GitHub, public, with placeholder README

---

## Phase 2 — Local ingest pipeline (Python)
**Estimated time:** 2 hours
**Goal:** `chunks.jsonl` file containing all Laravel docs chunked and embedded.

### Tasks
- [ ] Create `/ingest` directory with own `requirements.txt`
- [ ] Install: `sentence-transformers`, `markdown-it-py`, `tqdm`, `gitpython`
- [ ] Script `clone_docs.py` — clone `laravel/docs` GitHub repo to local cache
- [ ] Script `chunk_docs.py` — parse markdown files, split into ~500 token chunks with metadata (file path, section heading, source URL on laravel.com/docs)
- [ ] Script `embed_chunks.py` — generate 768-dim embeddings using `BAAI/bge-base-en-v1.5`
- [ ] Output: `chunks.jsonl` with `{id, text, embedding, metadata}` per line
- [ ] Add ingest README explaining how to re-run

### Verification
- `chunks.jsonl` exists, has ~2,000-3,000 lines
- Each line is valid JSON with 768-element embedding array
- Random sample: print one chunk's text + metadata, verify it makes sense

### Decision to log in DECISIONS.md
- Why local embedding instead of Workers AI? (free tier neuron budget)
- Why this chunk size? (trade-off: context vs retrieval precision)

---

## Phase 3 — Vectorize index & upload
**Estimated time:** 1 hour
**Goal:** Vectors live in Cloudflare Vectorize, queryable from Wrangler.

### Tasks
- [ ] Create Vectorize index via Wrangler: `wrangler vectorize create laravel-docs --dimensions=768 --metric=cosine`
- [ ] Add Vectorize binding to `wrangler.toml`
- [ ] Write Node.js script `upload_to_vectorize.ts` that reads `chunks.jsonl` and uploads in batches via Wrangler API
- [ ] Verify count via dashboard or `wrangler vectorize info`
- [ ] Test query: top-5 nearest neighbors for a sample embedding

### Verification
- Vectorize index reports correct count (~2,000-3,000)
- Manual query returns relevant chunks for a test question ("how do I define a route?")

---

## Phase 4 — `/api/ask` endpoint
**Estimated time:** 2-3 hours
**Goal:** Full RAG pipeline working — POST a question, get a streamed answer with citations.

### Tasks
- [ ] Add Workers AI binding to `wrangler.toml`
- [ ] Implement `/api/ask` POST route in Hono
- [ ] Pipeline:
  1. Validate request body with Zod (`{ question: string }`)
  2. Embed question via Workers AI (`@cf/baai/bge-base-en-v1.5`)
  3. Query Vectorize top-5 with returned embedding
  4. Build prompt with retrieved context (system + user + context)
  5. Call LLM (`@cf/meta/llama-3.1-8b-instruct`) with streaming
  6. Stream response back as SSE or ReadableStream
- [ ] Include citation metadata in response (source URLs)
- [ ] Handle errors explicitly (Vectorize miss, AI timeout, etc.)

### Verification
- `curl -X POST localhost:8787/api/ask -d '{"question":"how do I define a route in Laravel?"}'` streams a coherent answer
- Response includes references to actual Laravel docs URLs
- Bad input (empty question, wrong shape) returns 400 with clear error

### Decision to log
- Prompt template chosen and why
- Top-k value chosen and why

---

## Phase 5 — D1 logging & Durable Object rate limiting
**Estimated time:** 1.5 hours
**Goal:** Queries logged for analytics, rate limiting protects free tier from abuse.

### Tasks
- [ ] Create D1 database: `wrangler d1 create laravel-docs-qa`
- [ ] Schema: `queries` table (id, question, latency_ms, num_sources, created_at, ip_hash)
- [ ] Add D1 binding to `wrangler.toml`
- [ ] Insert log row at end of `/api/ask` (fire-and-forget, do not block response)
- [ ] Implement Durable Object `RateLimiter` with SQLite backend
  - Limit: 20 requests per IP per hour
  - Methods: `checkAndIncrement(ip): { allowed: boolean, remaining: number }`
- [ ] Wire DO into `/api/ask` — return 429 if exceeded, with `Retry-After` header
- [ ] Hash IP (don't store raw IP) for basic privacy

### Verification
- After 21 requests from same IP within an hour, 429 returned
- D1 table populated with query logs
- Old log entries still queryable

### Decision to log
- Why Durable Objects over KV for rate limiting
- IP hashing approach

---

## Phase 6 — Vue.js frontend
**Estimated time:** 2 hours
**Goal:** Clean chat UI deployed on Cloudflare Pages.

### Tasks
- [ ] Create separate `/frontend` directory with Vite + Vue 3
- [ ] Install Tailwind, configure
- [ ] Single page: input box, submit button, streaming answer area, citations list below
- [ ] Compose-API based, no Pinia/Vuex
- [ ] `useAsk()` composable wraps fetch to `/api/ask` and parses stream
- [ ] Loading states, error states
- [ ] Mobile responsive (Tailwind sm/md/lg breakpoints)
- [ ] Deploy to Cloudflare Pages
- [ ] Configure Pages to proxy `/api/*` to the Worker (or set Worker on subdomain)

### Verification
- Live URL works, can submit question, sees streaming answer with citations
- Works on mobile (test in browser dev tools)
- No console errors

### Decision to log
- Why Vue over React for this project
- Streaming consumption approach

---

## Phase 7 — Cron Trigger + Queues for re-indexing
**Estimated time:** 1 hour
**Goal:** Monthly automatic re-index of Laravel docs.

### Tasks
- [ ] Create Cloudflare Queue: `wrangler queues create reindex-jobs`
- [ ] Add Cron Trigger to `wrangler.toml` (1st of each month)
- [ ] Scheduled handler enqueues a job into the queue
- [ ] Queue consumer (separate Worker or same): for v1, just logs "re-index triggered" — full implementation noted as future work in README
- [ ] Document in README that production re-indexing would call the ingest pipeline (which is local for free tier reasons)

### Verification
- `wrangler triggers schedule` test invocation enqueues a job
- Queue consumer receives and processes the message

### Note
This phase is intentionally minimal because full re-indexing requires either Workers Paid plan or external compute. The point is to demonstrate the architecture, not necessarily to run it.

---

## Phase 8 — README, polish, public launch
**Estimated time:** 2 hours
**Goal:** Repo and demo ready to share with clients.

### Tasks
- [ ] Take 2-3 screenshots of working demo
- [ ] Record short GIF (use Kap, ScreenToGif, or similar) showing query → streamed answer
- [ ] Write README:
  - Title + 1-line description
  - Live demo link (top, prominent)
  - Screenshot/GIF
  - "What it does" — 2 paragraphs
  - "Architecture" — Mermaid or ASCII diagram + explanation
  - "Tech stack" — bulleted list
  - "How it works" — walk through pipeline step by step
  - "Cost analysis" — actual numbers for free tier vs paid (with 1K queries/day estimate)
  - "Trade-offs and decisions" — summarize from DECISIONS.md
  - "What I learned" — 3-5 bullets
  - "Running locally" — setup instructions
  - "Future work" — what would change for true production (Workers Paid, multi-tenant, conversation history)
- [ ] Add repo description, topics (`cloudflare-workers`, `rag`, `workers-ai`, `vectorize`, `laravel`, `vue`)
- [ ] Push final commit, tag `v1.0`

### Verification
- README reads well as a standalone document
- Live demo link works from incognito browser
- Anyone can clone, follow instructions, and get it running locally

---

## Total estimated time

**11-13 hours of focused work**, realistically spread over 2-3 days.

If anything blocks for more than 30 minutes, stop and reassess — either the design needs to change or the scope needs to shrink.

---

## Tracking

Use this file as a checklist. Check off tasks as you go. If you discover something that should be added, add it. If you decide to skip something, note why in `DECISIONS.md` rather than just removing it.