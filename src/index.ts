import { Hono } from 'hono';
import type { Env } from './bindings/env';
import { logQuery, hashIp } from './lib/logger';
import { RateLimiter } from './durable_objects/rate_limiter';

const app = new Hono<{ Bindings: Env }>();

// ============================================================
// Auth middleware — protects /api/* routes
// ============================================================
const authMiddleware = async (c: any, next: () => Promise<void>) => {
	const authHeader = c.req.header('Authorization');

	if (!authHeader || !authHeader.startsWith('Bearer ')) {
		return c.json({ error: 'Missing or invalid Authorization header' }, 401);
	}

	const token = authHeader.substring('Bearer '.length).trim();

	if (!token || token !== c.env.API_TOKEN) {
		return c.json({ error: 'Invalid token' }, 401);
	}

	await next();
};

// Apply auth to all /api/* routes
app.use('/api/*', authMiddleware);

// ============================================================
// /health — basic health check  PUBLIC (no auth)
// ============================================================
app.get('/health', (c) => {
	return c.json({
		status: 'ok',
		timestamp: Date.now(),
	});
});

// ============================================================
// /api/ask — RAG question answering PROTECTED (requires Bearer token)
// ============================================================
app.post('/api/ask', async (c) => {
	const startTime = Date.now();

	let body: { question?: string };

	try {
		body = await c.req.json();
	} catch {
		return c.json({ error: 'Invalid JSON in request body' }, 400);
	}

	const question = body.question?.trim();
	if (!question) {
		return c.json({ error: "Missing or empty 'question' field" }, 400);
	}

	if (question.length > 500) {
		return c.json({ error: 'Question too long (max 500 chars)' }, 400);
	}

	// ============ Before starting: Rate limit check  ============

	const clientIp = c.req.header('CF-Connecting-IP') || 'unknown';
	const ipHash = await hashIp(clientIp);

	const rateLimiterId = c.env.RATE_LIMITER.idFromName(ipHash);
	const rateLimiter = c.env.RATE_LIMITER.get(rateLimiterId);
	const rateLimitResult = await rateLimiter.checkAndIncrement();

	if (!rateLimitResult.allowed) {
		return c.json(
			{
				error: 'Rate limit exceeded',
				message: `Maximum 20 requests per hour. Try again in ${rateLimitResult.retryAfter} seconds.`,
			},
			429,
			{
				'Retry-After': String(rateLimitResult.retryAfter),
				'X-RateLimit-Limit': '20',
				'X-RateLimit-Remaining': '0',
			},
		);
	}
	// ====================================================

	try {
		// Step 1: Embed the question
		const embeddingResponse = await c.env.AI.run('@cf/baai/bge-base-en-v1.5', {
			text: [question],
		});
		const queryEmbedding = embeddingResponse.data[0];

		if (!queryEmbedding) {
			return c.json({ error: 'Failed to generate embedding' }, 500);
		}

		// Step 2: Query Vectorize for top-5 most similar chunks
		const searchResults = await c.env.VECTORIZE.query(queryEmbedding, {
			topK: 5,
			returnMetadata: 'all',
		});

		if (searchResults.matches.length === 0) {
			return c.json(
				{
					error: 'No relevant context found in knowledge base',
				},
				404,
			);
		}

		// Step 3: Build context from retrieved chunks
		const contextChunks = searchResults.matches
			.map((match, i) => {
				const meta = match.metadata as {
					text: string;
					source_url: string;
					h1?: string;
					h2?: string;
				};
				return `[Source ${i + 1}: ${meta.h1 ?? 'Unknown'}${meta.h2 ? ' > ' + meta.h2 : ''}]${meta.text}`;
			})
			.join('\n\n---\n\n');

		// Step 4: Build sources list (for response metadata)
		const sources = searchResults.matches.map((match) => {
			const meta = match.metadata as {
				source_url: string;
				h1?: string;
				h2?: string;
			};
			return {
				url: meta.source_url,
				section: meta.h1 + (meta.h2 ? ` > ${meta.h2}` : ''),
				score: match.score,
			};
		});

		// Step 5: Build prompt for LLM
		const systemPrompt = `You are a helpful assistant answering questions about the Laravel PHP framework. 
            Use ONLY the provided context from Laravel's official documentation. 
            If the context doesn't contain the answer, say so clearly — do not invent information.
            Be concise. When referencing code examples, format them clearly.
            Cite sources using [Source N] notation matching the numbered sources below.`;

		const userPrompt = `Context from Laravel documentation:

            ${contextChunks}

            ---

            Question: ${question}

            Answer (cite sources using [Source N]):`;

		// Step 6: Call LLM with streaming
		const llmStream = await c.env.AI.run('@cf/meta/llama-3.1-8b-instruct', {
			messages: [
				{ role: 'system', content: systemPrompt },
				{ role: 'user', content: userPrompt },
			],
			stream: true,
			max_tokens: 512,
		});

		// ============ Step 7: Log query asynchronously ============
		const latencyMs = Date.now() - startTime;

		// Fire-and-forget logging (doesn't block response)
		c.executionCtx.waitUntil(
			logQuery(c.env.DB, {
				question,
				latencyMs,
				numSources: searchResults.matches.length,
				ipHash,
			}),
		);
		// =======================================================

		// Step 8: Return streaming response with sources in custom header
		return new Response(llmStream as ReadableStream, {
			headers: {
				'Content-Type': 'text/event-stream',
				'Cache-Control': 'no-cache',
				'X-Sources': JSON.stringify(sources),
			},
		});
	} catch (error) {
		console.error('Error in /api/ask:', error);
		return c.json(
			{
				error: 'Internal server error',
				details: error instanceof Error ? error.message : 'Unknown',
			},
			500,
		);
	}
});

// ============================================================
// 404 handler
// ============================================================
app.notFound((c) => {
	return c.json({ error: 'Not Found' }, 404);
});

// MUST be re-exported for Workers runtime to discover the DO class
export { RateLimiter };

export default app;
