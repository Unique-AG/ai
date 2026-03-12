/**
 * Shared test helpers for tool tests.
 * Provides fetch mocking and common assertions.
 */

/** Create a mock Response object */
export function mockResponse(
  status: number,
  body: unknown,
  ok?: boolean
): Response {
  return {
    ok: ok ?? (status >= 200 && status < 300),
    status,
    json: async () => body,
    text: async () => (typeof body === "string" ? body : JSON.stringify(body)),
    headers: new Headers(),
  } as Response;
}

/**
 * Install a fetch mock that records calls and returns canned responses.
 * Returns a tracker object to inspect captured requests.
 */
export function mockFetch(
  responses: Array<{ status: number; body: unknown }> | { status: number; body: unknown }
) {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  const responseArray = Array.isArray(responses) ? responses : [responses];
  let callIndex = 0;

  globalThis.fetch = async (input, init) => {
    calls.push({ url: input as string, init });
    const resp = responseArray[Math.min(callIndex, responseArray.length - 1)];
    callIndex++;
    return mockResponse(resp.status, resp.body);
  };

  return {
    get calls() {
      return calls;
    },
    /** Get the URL path of the Nth call (0-indexed) */
    urlPath(n: number): string {
      const url = new URL(calls[n].url);
      return url.pathname;
    },
    /** Get query params of the Nth call */
    queryParams(n: number): URLSearchParams {
      const url = new URL(calls[n].url);
      return url.searchParams;
    },
  };
}
