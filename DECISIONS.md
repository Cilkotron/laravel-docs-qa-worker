## 2026-05-20 — Chose Hono framework over vanilla Workers

**Context:** Need routing and middleware for Workers API with multiple endpoints.

**Options considered:**
- Vanilla Workers (`fetch` handler with manual routing)
- itty-router (~1KB, minimalist)
- Hono (~12KB, full-featured)

**Choice:** Hono

**Why:** Industry standard for Cloudflare Workers in 2026, clean TypeScript 
typing, built-in Zod integration, streaming support out of the box. Portfolio 
projects benefit from familiar framework that potential clients recognize.

**Trade-offs:** Slightly larger bundle than vanilla (~12KB), but cold start 
impact is negligible.