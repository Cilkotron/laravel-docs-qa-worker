// Type definition for Worker bindings (environment)
// These come from wrangler.jsonc configuration

export type Env = {
	AI: Ai; // Workers AI binding (provided by @cloudflare/workers-types)
	VECTORIZE: Vectorize; // Vectorize binding
    API_TOKEN: string; // Bearer token for /api/ask authentication
};
