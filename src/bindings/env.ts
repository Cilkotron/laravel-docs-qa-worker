// Type definition for Worker bindings (environment)
// These come from wrangler.jsonc configuration
import type { RateLimiter } from "../durable_objects/rate_limiter";

export type Env = {
	AI: Ai; // Workers AI binding (provided by @cloudflare/workers-types)
	VECTORIZE: Vectorize; // Vectorize binding
	API_TOKEN: string; // Bearer token for /api/ask authentication
	DB: D1Database;
    RATE_LIMITER: DurableObjectNamespace<RateLimiter>;
};