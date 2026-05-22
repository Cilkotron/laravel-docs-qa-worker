/**
 * RateLimiter Durable Object
 * 
 * Tracks request count per IP, with a sliding window of 1 hour.
 * Uses SQLite-backed storage for atomic, durable state.
 * 
 * Usage:
 *   const id = env.RATE_LIMITER.idFromName(ipHash);
 *   const stub = env.RATE_LIMITER.get(id);
 *   const result = await stub.checkAndIncrement();
 *   if (!result.allowed) {
 *     // return 429 with Retry-After header
 *   }
 */

import { DurableObject } from "cloudflare:workers";

const RATE_LIMIT = 20;              // requests per hour
const WINDOW_MS = 60 * 60 * 1000;   // 1 hour in milliseconds

export class RateLimiter extends DurableObject {
  sql: SqlStorage;

  constructor(ctx: DurableObjectState, env: unknown) {
    super(ctx, env);
    this.sql = ctx.storage.sql;

    // Initialize table on first run
    this.sql.exec(`
      CREATE TABLE IF NOT EXISTS requests (
        timestamp INTEGER NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_timestamp ON requests(timestamp);
    `);
  }

  /**
   * Check if a request is allowed and increment counter.
   * 
   * @returns { allowed, remaining, retryAfter }
   *   - allowed: true if under limit, false if exceeded
   *   - remaining: how many requests left in this window
   *   - retryAfter: seconds until oldest request expires (only when blocked)
   */
  async checkAndIncrement(): Promise<{
    allowed: boolean;
    remaining: number;
    retryAfter?: number;
  }> {
    const now = Date.now();
    const windowStart = now - WINDOW_MS;

    // Clean up old entries (older than 1 hour)
    this.sql.exec("DELETE FROM requests WHERE timestamp < ?", windowStart);

    // Count current requests in the window
    const result = this.sql
      .exec("SELECT COUNT(*) as count FROM requests")
      .one() as { count: number };

    const currentCount = result.count;

    if (currentCount >= RATE_LIMIT) {
      // Find oldest entry to determine when it will expire
      const oldest = this.sql
        .exec("SELECT MIN(timestamp) as oldest FROM requests")
        .one() as { oldest: number };

      const retryAfterMs = oldest.oldest + WINDOW_MS - now;
      const retryAfter = Math.ceil(retryAfterMs / 1000);

      return {
        allowed: false,
        remaining: 0,
        retryAfter: Math.max(retryAfter, 1),
      };
    }

    // Record this request
    this.sql.exec("INSERT INTO requests (timestamp) VALUES (?)", now);

    return {
      allowed: true,
      remaining: RATE_LIMIT - currentCount - 1,
    };
  }
}