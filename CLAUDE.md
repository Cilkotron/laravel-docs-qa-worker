# Project: Docs Q&A — RAG over Laravel Documentation

## Goal

Production-grade RAG chatbot that answers questions about Laravel documentation, with cited sources. Built entirely on Cloudflare's stack. Public portfolio project demonstrating production RAG patterns.

## Why this project

Showcase real production RAG experience (Workers AI, Vectorize, edge inference) for freelance/contract clients. Live demo + clean code + thoughtful README are the deliverable — not just a working app.

## Stack (do not deviate without discussion)

### Backend (Cloudflare Workers)
- **Runtime:** Cloudflare Workers, TypeScript, strict mode
- **Framework:** Hono (lightweight, edge-native)
- **AI:** Workers AI
  - Embeddings: `@cf/baai/bge-base-en-v1.5` (768 dimensions)
  - LLM: `@cf/meta/llama-3.1-8b-instruct` (streaming responses)
- **Vector storage:** Vectorize (single index, 768 dimensions, cosine similarity)
- **Relational storage:** D1 (query logs, analytics)
- **Rate limiting:** Durable Objects with SQLite backend (NOT KV — free tier writes are too low)
- **Scheduled jobs:** Cron Triggers for monthly re-indexing
- **Queues:** Cloudflare Queues for async re-index processing

### Ingest pipeline (local, Python)
- **Why local:** stays under Workers AI free tier daily neuron limit
- **Language:** Python 3.11+
- **Embedding model:** `sentence-transformers/BAAI/bge-base-en-v1.5` (same model as runtime, ensures vector compatibility)
- **Source:** clone of `laravel/docs` GitHub repo
- **Output:** JSON file with chunks + embeddings, uploaded to Vectorize via Wrangler

### Frontend
- **Framework:** Vue.js 3 with Composition API
- **Build tool:** Vite
- **Styling:** Tailwind CSS
- **Deploy:** Cloudflare Pages
- **No state management library** — `ref` and `reactive` are enough

## Constraints

### Must-haves
- Everything must work on Cloudflare free tier (Workers Free plan, no Workers Paid required)
- No external API dependencies (no OpenAI, no Pinecone, no Anthropic API in production)
- TypeScript strict mode, no `any` without justified comment
- Streaming LLM responses (Server-Sent Events or ReadableStream)
- All errors handled explicitly — no silent catches

### Nice-to-haves
- Sub-second response start for queries (TTFB after embedding)
- Citation links back to official Laravel docs URLs
- Mobile-friendly UI (Tailwind responsive utilities)

### Out of scope
- User authentication / login
- Multi-tenant features
- Conversation history / multi-turn (single Q&A only for v1)
- Admin panel
- Tests beyond critical path smoke tests (this is a portfolio project, not a production SaaS)

## Code style

### General
- Functional approach where possible; classes only for Durable Objects and where stateful encapsulation is genuinely needed
- Explicit over clever — readable code wins over compact code
- Errors handled with discriminated unions or thrown with typed error classes, never silent

### TypeScript
- Strict mode, `noUncheckedIndexedAccess: true`
- Prefer `type` over `interface` for object shapes
- Inferred return types are fine; explicit on exported functions
- Use Zod for runtime validation of external inputs (request bodies, query params)

### File organization
```
/src
  /routes        — Hono route handlers, one file per domain (ask.ts, health.ts)
  /lib           — Reusable pure functions (chunking, prompt building, etc.)
  /bindings      — Type definitions for Worker bindings (AI, Vectorize, D1, DO)
  /durable       — Durable Object classes (rate-limiter.ts)
  index.ts       — Main Worker entry, Hono app setup
/ingest          — Python ingest pipeline (separate from Worker code)
/frontend        — Vue.js Pages project (separate package.json)
```

### Naming
- Files: `kebab-case.ts`
- Variables/functions: `camelCase`
- Types/classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE` only for true compile-time constants

## What I'm doing vs what Claude Code is doing

This is an AI-assisted project. Claude Code accelerates implementation but does not own decisions.

### I own (do not change without asking me)
- Architecture choices (why Vectorize over Pinecone, why local ingest, why Durable Objects over KV)
- Free-tier strategy
- API surface design (`/api/ask`, response shapes)
- README narrative and positioning
- Trade-off documentation in `DECISIONS.md`

### Claude Code does
- Implementation of agreed-upon design
- Boilerplate (Wrangler config, TypeScript setup, Hono route skeletons)
- Test scaffolding
- Type definitions
- Refactoring suggestions

### Rules of engagement
- Work in small steps, one feature at a time
- Always show diff before applying
- After any significant change, run `wrangler dev` to verify it still works
- Commit after each working step with a clear message
- Update `DECISIONS.md` when making non-obvious choices

## Documentation references

When implementing Cloudflare features, prefer the actual current docs over training data — APIs change:
- Workers AI: https://developers.cloudflare.com/workers-ai/
- Vectorize: https://developers.cloudflare.com/vectorize/
- D1: https://developers.cloudflare.com/d1/
- Durable Objects: https://developers.cloudflare.com/durable-objects/
- Hono on Workers: https://hono.dev/docs/getting-started/cloudflare-workers

If you're unsure about a binding signature or API method, ask me to paste the relevant docs section. Do not guess.

## Definition of done (for portfolio purposes)

The project is "done enough to share" when:
1. Live demo URL works (workers.dev subdomain is fine)
2. End-to-end query → cited answer takes under 5 seconds
3. README has: live demo link, screenshot/GIF, architecture diagram, tech stack, "how it works" section, cost analysis, trade-offs section
4. Code is clean enough to send to a senior reviewer without embarrassment
5. `DECISIONS.md` documents 5-10 key trade-offs made during development
6. GitHub repo is public, has good description and topics