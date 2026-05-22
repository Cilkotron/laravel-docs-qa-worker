/**
 * Asynchronously log a query to D1.
 * 
 * Fire-and-forget: this function should be called with `ctx.waitUntil()`
 * so it doesn't block the response.
 */
export async function logQuery(
  db: D1Database,
  params: {
    question: string;
    latencyMs: number;
    numSources: number;
    ipHash: string;
  }
): Promise<void> {
  const id = crypto.randomUUID();
  try {
    await db
      .prepare(
        `INSERT INTO queries (id, question, latency_ms, num_sources, ip_hash) 
         VALUES (?, ?, ?, ?, ?)`
      )
      .bind(id, params.question, params.latencyMs, params.numSources, params.ipHash)
      .run();
  } catch (error) {
    // Log errors but don't throw — logging failures shouldn't break the request
    console.error("Failed to log query:", error);
  }
}

/**
 * Hash an IP address using SHA-256 for basic privacy.
 * 
 * Returns a hex-encoded string. Not cryptographic security, just
 * privacy-friendly so we don't store raw IPs.
 */
export async function hashIp(ip: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(ip);
  const hash = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hash))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("")
    .slice(0, 16); // First 16 hex chars = enough uniqueness, smaller storage
}