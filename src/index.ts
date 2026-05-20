import { Hono } from "hono";

const app = new Hono();

app.get("/health", (c) => {
  return c.json({
    status: "ok",
    timestamp: Date.now(),
  });
});

app.notFound((c) => {
  return c.json({ error: "Not Found" }, 404);
});

export default app;