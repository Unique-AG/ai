import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import express from "express";
import type { Server } from "node:http";

const CLIENT_ID = "test-client-id";
const CLIENT_SECRET = "test-client-secret";

let server: Server;
let baseUrl: string;

async function startApp() {
  const mod = await import("../middleware");
  const app = express();
  app.use(mod.default.router);
  // Protected route to test bearer middleware
  app.get("/mcp", mod.default.middleware, (_req, res) => {
    res.json({ ok: true });
  });
  return new Promise<void>((resolve) => {
    server = app.listen(0, () => {
      const addr = server.address();
      if (addr && typeof addr === "object") {
        baseUrl = `http://127.0.0.1:${addr.port}`;
      }
      resolve();
    });
  });
}

function stopApp() {
  return new Promise<void>((resolve) => {
    if (server) server.close(() => resolve());
    else resolve();
  });
}

function basicAuth(id: string, secret: string): string {
  return "Basic " + Buffer.from(`${id}:${secret}`).toString("base64");
}

describe("middleware", () => {
  let originalId: string | undefined;
  let originalSecret: string | undefined;

  beforeEach(async () => {
    originalId = process.env.MCP_CLIENT_ID;
    originalSecret = process.env.MCP_CLIENT_SECRET;
    process.env.MCP_CLIENT_ID = CLIENT_ID;
    process.env.MCP_CLIENT_SECRET = CLIENT_SECRET;
    await startApp();
  });

  afterEach(async () => {
    await stopApp();
    if (originalId !== undefined) process.env.MCP_CLIENT_ID = originalId;
    else delete process.env.MCP_CLIENT_ID;
    if (originalSecret !== undefined) process.env.MCP_CLIENT_SECRET = originalSecret;
    else delete process.env.MCP_CLIENT_SECRET;
  });

  // ── CORS ──────────────────────────────────────────────────────────

  describe("CORS", () => {
    it("returns CORS headers on preflight OPTIONS", async () => {
      const res = await fetch(`${baseUrl}/mcp`, { method: "OPTIONS" });
      assert.strictEqual(res.status, 204);
      assert.strictEqual(res.headers.get("access-control-allow-origin"), "*");
      assert.ok(res.headers.get("access-control-allow-methods")?.includes("POST"));
      assert.ok(res.headers.get("access-control-allow-headers")?.includes("Authorization"));
    });
  });

  // ── OAuth Discovery ───────────────────────────────────────────────

  describe("GET /.well-known/oauth-protected-resource", () => {
    it("returns resource metadata with authorization server", async () => {
      const res = await fetch(`${baseUrl}/.well-known/oauth-protected-resource`);
      assert.strictEqual(res.status, 200);
      const body = await res.json();
      assert.strictEqual(body.resource, `${baseUrl}/mcp`);
      assert.ok(Array.isArray(body.authorization_servers));
      assert.strictEqual(body.authorization_servers[0], baseUrl);
    });

    it("falls through when auth is disabled", async () => {
      delete process.env.MCP_CLIENT_ID;
      delete process.env.MCP_CLIENT_SECRET;
      const res = await fetch(`${baseUrl}/.well-known/oauth-protected-resource`);
      // No route handler after the router, so Express returns 404
      assert.strictEqual(res.status, 404);
    });
  });

  describe("GET /.well-known/oauth-authorization-server", () => {
    it("returns authorization server metadata", async () => {
      const res = await fetch(`${baseUrl}/.well-known/oauth-authorization-server`);
      assert.strictEqual(res.status, 200);
      const body = await res.json();
      assert.strictEqual(body.issuer, baseUrl);
      assert.strictEqual(body.token_endpoint, `${baseUrl}/token`);
      assert.strictEqual(body.authorization_endpoint, `${baseUrl}/authorize`);
      assert.strictEqual(body.registration_endpoint, `${baseUrl}/register`);
      assert.deepStrictEqual(body.token_endpoint_auth_methods_supported, [
        "client_secret_basic",
        "client_secret_post",
      ]);
      assert.deepStrictEqual(body.code_challenge_methods_supported, ["S256"]);
    });
  });

  // ── POST /register ────────────────────────────────────────────────

  describe("POST /register", () => {
    it("returns 201 with valid client credentials", async () => {
      const res = await fetch(`${baseUrl}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: CLIENT_ID, client_secret: CLIENT_SECRET }),
      });
      assert.strictEqual(res.status, 201);
      const body = await res.json();
      assert.strictEqual(body.client_id, CLIENT_ID);
    });

    it("returns 401 with invalid credentials", async () => {
      const res = await fetch(`${baseUrl}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: CLIENT_ID, client_secret: "wrong" }),
      });
      assert.strictEqual(res.status, 401);
      const body = await res.json();
      assert.strictEqual(body.error, "invalid_client");
    });

    it("returns 401 with missing body", async () => {
      const res = await fetch(`${baseUrl}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      assert.strictEqual(res.status, 401);
    });
  });

  // ── GET /authorize ────────────────────────────────────────────────

  describe("GET /authorize", () => {
    it("redirects with code and state for valid request", async () => {
      const redirectUri = "http://localhost:9999/callback";
      const params = new URLSearchParams({
        response_type: "code",
        client_id: CLIENT_ID,
        redirect_uri: redirectUri,
        code_challenge: "test-challenge",
        state: "test-state",
      });
      const res = await fetch(`${baseUrl}/authorize?${params}`, { redirect: "manual" });
      assert.strictEqual(res.status, 302);
      const location = res.headers.get("location")!;
      const url = new URL(location);
      assert.ok(url.searchParams.has("code"));
      assert.strictEqual(url.searchParams.get("state"), "test-state");
      assert.strictEqual(url.origin + url.pathname, redirectUri);
    });

    it("returns 400 for missing response_type", async () => {
      const params = new URLSearchParams({
        client_id: CLIENT_ID,
        redirect_uri: "http://localhost:9999/callback",
        code_challenge: "test-challenge",
      });
      const res = await fetch(`${baseUrl}/authorize?${params}`);
      assert.strictEqual(res.status, 400);
      const body = await res.json();
      assert.strictEqual(body.error, "invalid_request");
    });

    it("returns 400 for missing redirect_uri", async () => {
      const params = new URLSearchParams({
        response_type: "code",
        client_id: CLIENT_ID,
        code_challenge: "test-challenge",
      });
      const res = await fetch(`${baseUrl}/authorize?${params}`);
      assert.strictEqual(res.status, 400);
    });

    it("returns 400 for missing code_challenge", async () => {
      const params = new URLSearchParams({
        response_type: "code",
        client_id: CLIENT_ID,
        redirect_uri: "http://localhost:9999/callback",
      });
      const res = await fetch(`${baseUrl}/authorize?${params}`);
      assert.strictEqual(res.status, 400);
    });
  });

  // ── POST /token ───────────────────────────────────────────────────

  describe("POST /token", () => {
    describe("client_credentials grant", () => {
      it("returns access token with Basic auth", async () => {
        const res = await fetch(`${baseUrl}/token`, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            Authorization: basicAuth(CLIENT_ID, CLIENT_SECRET),
          },
          body: "grant_type=client_credentials",
        });
        assert.strictEqual(res.status, 200);
        const body = await res.json();
        assert.ok(body.access_token);
        assert.strictEqual(body.token_type, "bearer");
        assert.strictEqual(body.expires_in, 3600);
        assert.strictEqual(res.headers.get("cache-control"), "no-store");
      });

      it("returns access token with client_secret_post", async () => {
        const res = await fetch(`${baseUrl}/token`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: `grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}`,
        });
        assert.strictEqual(res.status, 200);
        const body = await res.json();
        assert.ok(body.access_token);
        assert.strictEqual(body.token_type, "bearer");
      });

      it("returns 401 with wrong Basic auth", async () => {
        const res = await fetch(`${baseUrl}/token`, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            Authorization: basicAuth(CLIENT_ID, "wrong-secret"),
          },
          body: "grant_type=client_credentials",
        });
        assert.strictEqual(res.status, 401);
        const body = await res.json();
        assert.strictEqual(body.error, "invalid_client");
      });

      it("returns 401 with no credentials", async () => {
        const res = await fetch(`${baseUrl}/token`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: "grant_type=client_credentials",
        });
        assert.strictEqual(res.status, 401);
      });
    });

    describe("authorization_code grant", () => {
      async function getAuthCode(): Promise<string> {
        const params = new URLSearchParams({
          response_type: "code",
          client_id: CLIENT_ID,
          redirect_uri: "http://localhost:9999/callback",
          code_challenge: "test-challenge",
        });
        const res = await fetch(`${baseUrl}/authorize?${params}`, { redirect: "manual" });
        const location = res.headers.get("location")!;
        return new URL(location).searchParams.get("code")!;
      }

      it("exchanges valid code for access token", async () => {
        const code = await getAuthCode();
        const res = await fetch(`${baseUrl}/token`, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            Authorization: basicAuth(CLIENT_ID, CLIENT_SECRET),
          },
          body: `grant_type=authorization_code&code=${code}`,
        });
        assert.strictEqual(res.status, 200);
        const body = await res.json();
        assert.ok(body.access_token);
        assert.strictEqual(body.token_type, "bearer");
        assert.strictEqual(body.expires_in, 3600);
      });

      it("rejects reused authorization code", async () => {
        const code = await getAuthCode();
        // First use — should succeed
        await fetch(`${baseUrl}/token`, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            Authorization: basicAuth(CLIENT_ID, CLIENT_SECRET),
          },
          body: `grant_type=authorization_code&code=${code}`,
        });
        // Second use — should fail
        const res = await fetch(`${baseUrl}/token`, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            Authorization: basicAuth(CLIENT_ID, CLIENT_SECRET),
          },
          body: `grant_type=authorization_code&code=${code}`,
        });
        assert.strictEqual(res.status, 400);
        const body = await res.json();
        assert.strictEqual(body.error, "invalid_grant");
      });

      it("rejects invalid authorization code", async () => {
        const res = await fetch(`${baseUrl}/token`, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            Authorization: basicAuth(CLIENT_ID, CLIENT_SECRET),
          },
          body: "grant_type=authorization_code&code=invalid-code",
        });
        assert.strictEqual(res.status, 400);
        const body = await res.json();
        assert.strictEqual(body.error, "invalid_grant");
      });
    });

    it("returns 400 for unsupported grant type", async () => {
      const res = await fetch(`${baseUrl}/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          Authorization: basicAuth(CLIENT_ID, CLIENT_SECRET),
        },
        body: "grant_type=password",
      });
      assert.strictEqual(res.status, 400);
      const body = await res.json();
      assert.strictEqual(body.error, "unsupported_grant_type");
    });
  });

  // ── Bearer middleware ─────────────────────────────────────────────

  describe("bearer token validation", () => {
    async function getToken(): Promise<string> {
      const res = await fetch(`${baseUrl}/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          Authorization: basicAuth(CLIENT_ID, CLIENT_SECRET),
        },
        body: "grant_type=client_credentials",
      });
      const body = await res.json();
      return body.access_token;
    }

    it("allows access with valid bearer token", async () => {
      const token = await getToken();
      const res = await fetch(`${baseUrl}/mcp`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      assert.strictEqual(res.status, 200);
      const body = await res.json();
      assert.strictEqual(body.ok, true);
    });

    it("returns 401 without Authorization header", async () => {
      const res = await fetch(`${baseUrl}/mcp`);
      assert.strictEqual(res.status, 401);
      const body = await res.json();
      assert.strictEqual(body.error, "invalid_token");
      assert.ok(res.headers.get("www-authenticate")?.includes("Bearer"));
    });

    it("returns 401 for invalid bearer token", async () => {
      const res = await fetch(`${baseUrl}/mcp`, {
        headers: { Authorization: "Bearer not-a-real-token" },
      });
      assert.strictEqual(res.status, 401);
      const body = await res.json();
      assert.strictEqual(body.error, "invalid_token");
    });

    it("skips auth entirely when env vars are unset", async () => {
      delete process.env.MCP_CLIENT_ID;
      delete process.env.MCP_CLIENT_SECRET;
      const res = await fetch(`${baseUrl}/mcp`);
      assert.strictEqual(res.status, 200);
    });
  });

  // ── Full OAuth flow ───────────────────────────────────────────────

  describe("full OAuth flow", () => {
    it("register → client_credentials token → protected resource", async () => {
      // Step 1: Register
      const regRes = await fetch(`${baseUrl}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: CLIENT_ID, client_secret: CLIENT_SECRET }),
      });
      assert.strictEqual(regRes.status, 201);

      // Step 2: Get token
      const tokenRes = await fetch(`${baseUrl}/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          Authorization: basicAuth(CLIENT_ID, CLIENT_SECRET),
        },
        body: "grant_type=client_credentials",
      });
      assert.strictEqual(tokenRes.status, 200);
      const { access_token } = await tokenRes.json();

      // Step 3: Access protected resource
      const mcpRes = await fetch(`${baseUrl}/mcp`, {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      assert.strictEqual(mcpRes.status, 200);
    });

    it("authorize → authorization_code token → protected resource", async () => {
      // Step 1: Get auth code
      const params = new URLSearchParams({
        response_type: "code",
        client_id: CLIENT_ID,
        redirect_uri: "http://localhost:9999/callback",
        code_challenge: "test-challenge",
        state: "my-state",
      });
      const authRes = await fetch(`${baseUrl}/authorize?${params}`, { redirect: "manual" });
      assert.strictEqual(authRes.status, 302);
      const code = new URL(authRes.headers.get("location")!).searchParams.get("code")!;

      // Step 2: Exchange code for token
      const tokenRes = await fetch(`${baseUrl}/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          Authorization: basicAuth(CLIENT_ID, CLIENT_SECRET),
        },
        body: `grant_type=authorization_code&code=${code}`,
      });
      assert.strictEqual(tokenRes.status, 200);
      const { access_token } = await tokenRes.json();

      // Step 3: Access protected resource
      const mcpRes = await fetch(`${baseUrl}/mcp`, {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      assert.strictEqual(mcpRes.status, 200);
    });
  });
});
