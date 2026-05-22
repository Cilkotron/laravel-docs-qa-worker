-- Migration: create queries table for logging
-- Run with: npx wrangler d1 execute laravel-docs-qa --file=migrations/0001_create_queries.sql

CREATE TABLE IF NOT EXISTS queries (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    latency_ms INTEGER NOT NULL,
    num_sources INTEGER NOT NULL,
    ip_hash TEXT NOT NULL,
    created_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000)
);

CREATE INDEX IF NOT EXISTS idx_queries_created_at ON queries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_queries_ip_hash ON queries(ip_hash);