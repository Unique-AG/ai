/**
 * OAuth 2.0 middleware for MCP server authentication.
 *
 * Auth is enabled when both MCP_CLIENT_ID and MCP_CLIENT_SECRET env vars are set.
 * When unset, all auth endpoints fall through (open access for local dev).
 *
 * Flow:
 *  1. Client calls POST /register with { client_id, client_secret } to validate
 *     its pre-shared credentials.
 *  2. Client obtains a token via POST /token using either:
 *     - grant_type=client_credentials (machine-to-machine), or
 *     - grant_type=authorization_code (after GET /authorize redirect flow with PKCE).
 *     Client authenticates with client_secret_basic (HTTP Basic) or client_secret_post.
 *  3. Client sends the token as `Authorization: Bearer <token>` on MCP requests.
 *
 * Token storage:
 *  - Tokens and auth codes are stored in-memory (Map). They are lost on server restart
 *    and do not replicate across processes. This is suitable for single-process deployments.
 *  - Tokens expire after 3 days (TOKEN_LIFETIME = 259200 s). Expired tokens/auth codes are swept
 *    from memory periodically and also removed on direct lookup when expired.
 *  - There is no revocation endpoint — tokens can only expire naturally.
 */
import express, { Router, type RequestHandler } from "express";
import { randomUUID, createHash } from "node:crypto";

/** In-memory store of active bearer tokens, keyed by token string. */
const tokens = new Map<string, { clientId: string; expiresAt: number }>();
/** In-memory store of pending authorization codes (PKCE flow). */
const authCodes = new Map<
  string,
  {
    clientId: string;
    codeChallenge: string;
    redirectUri: string;
    expiresAt: number;
  }
>();
export const TOKEN_LIFETIME = 259200; // 3 days in seconds
const CODE_LIFETIME = 60; // 1 minute in seconds
const CLEANUP_INTERVAL_MS = 60_000;

function sweepExpiredEntries(now = Math.floor(Date.now() / 1000)): void {
  for (const [token, info] of tokens) {
    if (info.expiresAt < now) tokens.delete(token);
  }
  for (const [code, info] of authCodes) {
    if (info.expiresAt < now) authCodes.delete(code);
  }
}

const cleanupTimer = setInterval(() => {
  sweepExpiredEntries();
}, CLEANUP_INTERVAL_MS);
cleanupTimer.unref();

function authEnabled(): boolean {
  return !!(process.env.MCP_CLIENT_ID && process.env.MCP_CLIENT_SECRET);
}

/** Derives the public base URL from the request, respecting reverse-proxy headers (e.g. ngrok). */
function getBaseUrl(req?: {
  headers: Record<string, string | string[] | undefined>;
}): string {
  if (req) {
    const forwardedHost = req.headers["x-forwarded-host"] as string | undefined;
    const forwardedProto = req.headers["x-forwarded-proto"] as
      | string
      | undefined;
    if (forwardedHost) {
      const proto = forwardedProto || "https";
      return `${proto}://${forwardedHost}`;
    }
    const host = req.headers["host"] as string | undefined;
    if (host) {
      const proto = forwardedProto || "http";
      return `${proto}://${host}`;
    }
  }
  const port = process.env.PORT || "3001";
  const host = process.env.HOST || "localhost";
  return `http://${host}:${port}`;
}

const router = Router();

// CORS
router.use((_req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader(
    "Access-Control-Allow-Headers",
    "Content-Type, Authorization, MCP-Protocol-Version",
  );
  if (_req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }
  next();
});

// RFC 9728 — Protected Resource Metadata
router.get("/.well-known/oauth-protected-resource", (req, res, next) => {
  if (!authEnabled()) return next();
  const base = getBaseUrl(req);
  res.json({ resource: `${base}/mcp`, authorization_servers: [base] });
});

// RFC 8414 — Authorization Server Metadata
router.get("/.well-known/oauth-authorization-server", (req, res, next) => {
  if (!authEnabled()) return next();
  const base = getBaseUrl(req);
  res.json({
    issuer: base,
    authorization_endpoint: `${base}/authorize`,
    token_endpoint: `${base}/token`,
    registration_endpoint: `${base}/register`,
    token_endpoint_auth_methods_supported: [
      "client_secret_basic",
      "client_secret_post",
    ],
    grant_types_supported: ["authorization_code", "client_credentials"],
    response_types_supported: ["code"],
    code_challenge_methods_supported: ["S256"],
  });
});

// Dynamic client registration — validates pre-shared credentials
router.post("/register", express.json(), (req, res, next) => {
  if (!authEnabled()) return next();

  const { client_id, client_secret } = req.body ?? {};
  if (
    client_id !== process.env.MCP_CLIENT_ID ||
    client_secret !== process.env.MCP_CLIENT_SECRET
  ) {
    res
      .status(401)
      .json({
        error: "invalid_client",
        error_description: "Invalid client credentials",
      });
    return;
  }

  res.status(201).json({ client_id });
});

// Authorization endpoint — auto-approves and redirects with code
router.get("/authorize", (req, res, next) => {
  if (!authEnabled()) return next();
  sweepExpiredEntries();

  const {
    client_id,
    redirect_uri,
    state,
    code_challenge,
    code_challenge_method,
    response_type,
  } = req.query;

  if (
    response_type !== "code" ||
    !redirect_uri ||
    !code_challenge ||
    !client_id
  ) {
    res.status(400).json({ error: "invalid_request" });
    return;
  }

  if (code_challenge_method !== undefined && code_challenge_method !== "S256") {
    res
      .status(400)
      .json({
        error: "invalid_request",
        error_description:
          "Unsupported code_challenge_method: only S256 is supported",
      });
    return;
  }

  if (client_id !== process.env.MCP_CLIENT_ID) {
    res.status(401).json({ error: "invalid_client" });
    return;
  }

  const code = randomUUID();
  authCodes.set(code, {
    clientId: client_id as string,
    codeChallenge: code_challenge as string,
    redirectUri: redirect_uri as string,
    expiresAt: Math.floor(Date.now() / 1000) + CODE_LIFETIME,
  });

  const url = new URL(redirect_uri as string);
  url.searchParams.set("code", code);
  if (state) url.searchParams.set("state", state as string);
  res.redirect(302, url.toString());
});

// Token endpoint
router.post(
  "/token",
  express.urlencoded({ extended: false }),
  (req, res, next) => {
    if (!authEnabled()) return next();

    const now = Math.floor(Date.now() / 1000);
    sweepExpiredEntries(now);
    const grantType = req.body?.grant_type;

    // Authenticate client (Basic header or body params)
    let clientId: string | undefined;
    const authHeader = req.headers.authorization;
    if (authHeader?.startsWith("Basic ")) {
      const decoded = Buffer.from(authHeader.slice(6), "base64").toString();
      const i = decoded.indexOf(":");
      if (
        i !== -1 &&
        decoded.slice(0, i) === process.env.MCP_CLIENT_ID &&
        decoded.slice(i + 1) === process.env.MCP_CLIENT_SECRET
      ) {
        clientId = decoded.slice(0, i);
      }
    } else if (
      req.body?.client_id === process.env.MCP_CLIENT_ID &&
      req.body?.client_secret === process.env.MCP_CLIENT_SECRET
    ) {
      clientId = req.body.client_id as string;
    }

    if (!clientId) {
      res.status(401).json({ error: "invalid_client" });
      return;
    }

    if (grantType === "authorization_code") {
      const codeInfo = authCodes.get(req.body.code);
      if (!codeInfo || codeInfo.expiresAt < now) {
        if (codeInfo) authCodes.delete(req.body.code);
        res.status(400).json({ error: "invalid_grant" });
        return;
      }
      authCodes.delete(req.body.code);

      // Validate redirect_uri matches what was presented at /authorize (RFC 6749 §4.1.3)
      if (req.body.redirect_uri !== codeInfo.redirectUri) {
        res
          .status(400)
          .json({
            error: "invalid_grant",
            error_description: "redirect_uri mismatch",
          });
        return;
      }

      // PKCE: validate code_verifier against stored code_challenge (S256)
      const codeVerifier = req.body.code_verifier;
      if (!codeVerifier) {
        res
          .status(400)
          .json({
            error: "invalid_request",
            error_description: "Missing code_verifier",
          });
        return;
      }
      const computed = createHash("sha256")
        .update(codeVerifier)
        .digest("base64url");
      if (computed !== codeInfo.codeChallenge) {
        res
          .status(400)
          .json({
            error: "invalid_grant",
            error_description: "PKCE code_verifier mismatch",
          });
        return;
      }

      const accessToken = randomUUID();
      tokens.set(accessToken, { clientId, expiresAt: now + TOKEN_LIFETIME });
      res.setHeader("Cache-Control", "no-store");
      res.json({
        access_token: accessToken,
        token_type: "Bearer",
        expires_in: TOKEN_LIFETIME,
      });
      return;
    }

    if (grantType === "client_credentials") {
      const accessToken = randomUUID();
      tokens.set(accessToken, { clientId, expiresAt: now + TOKEN_LIFETIME });
      res.setHeader("Cache-Control", "no-store");
      res.json({
        access_token: accessToken,
        token_type: "Bearer",
        expires_in: TOKEN_LIFETIME,
      });
      return;
    }

    res.status(400).json({ error: "unsupported_grant_type" });
  },
);

// Bearer token validation on MCP requests
const middleware: RequestHandler = (req, res, next) => {
  if (!authEnabled()) return next();
  sweepExpiredEntries();

  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith("Bearer ")) {
    const base = getBaseUrl(req);
    res
      .status(401)
      .setHeader(
        "WWW-Authenticate",
        `Bearer resource_metadata="${base}/.well-known/oauth-protected-resource"`,
      )
      .json({
        error: "invalid_token",
        error_description: "Missing Bearer token",
      });
    return;
  }

  const token = authHeader.slice(7);
  const info = tokens.get(token);
  if (!info || info.expiresAt < Math.floor(Date.now() / 1000)) {
    if (info) tokens.delete(token);
    res
      .status(401)
      .json({
        error: "invalid_token",
        error_description: "Invalid or expired token",
      });
    return;
  }

  (req as unknown as Record<string, unknown>).auth = {
    token,
    clientId: info.clientId,
    scopes: [],
    expiresAt: info.expiresAt,
  };
  next();
};

export default { router, middleware };
