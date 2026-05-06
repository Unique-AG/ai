import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import searchOfficers, { metadata } from "../../tools/search-officers";
import { mockFetch } from "./test-helpers";

describe("search-officers tool", () => {
  let originalFetch: typeof globalThis.fetch;
  let originalEnv: string | undefined;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    originalEnv = process.env.COMPANIES_HOUSE_API_KEY;
    process.env.COMPANIES_HOUSE_API_KEY = "test-key";
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    if (originalEnv !== undefined) {
      process.env.COMPANIES_HOUSE_API_KEY = originalEnv;
    } else {
      delete process.env.COMPANIES_HOUSE_API_KEY;
    }
  });

  describe("metadata", () => {
    it("should have the correct name", () => {
      assert.equal(metadata.name, "search-officers");
    });

    it("should have required MCP annotations", () => {
      assert.equal(metadata.annotations?.readOnlyHint, true);
      assert.equal(metadata.annotations?.destructiveHint, false);
      assert.equal(metadata.annotations?.idempotentHint, true);
    });
  });

  describe("validation", () => {
    it("should return error when neither query nor officerId provided", async () => {
      const result = await searchOfficers({});

      assert.match(result, /Error/);
      assert.match(result, /query/);
      assert.match(result, /officerId/);
    });

    it("should return error when both query and officerId provided", async () => {
      const result = await searchOfficers({
        query: "John",
        officerId: "abc123",
      });

      assert.match(result, /Error/);
      assert.match(result, /not both/);
    });
  });

  describe("search mode (query)", () => {
    it("should call /search/officers with query", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await searchOfficers({ query: "John Smith" });

      assert.equal(tracker.calls.length, 1);
      assert.equal(tracker.urlPath(0), "/search/officers");
      assert.equal(tracker.queryParams(0).get("q"), "John Smith");
    });

    it("should pass pagination params", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await searchOfficers({
        query: "John",
        itemsPerPage: 5,
        startIndex: 10,
      });

      assert.equal(tracker.queryParams(0).get("items_per_page"), "5");
      assert.equal(tracker.queryParams(0).get("start_index"), "10");
    });
  });

  describe("appointments mode (officerId)", () => {
    it("should call /officers/{id}/appointments", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await searchOfficers({ officerId: "abc123" });

      assert.equal(tracker.calls.length, 1);
      assert.equal(tracker.urlPath(0), "/officers/abc123/appointments");
    });

    it("should pass filter param", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await searchOfficers({
        officerId: "abc123",
        filter: "active",
      });

      assert.equal(tracker.queryParams(0).get("filter"), "active");
    });

    it("should return error on API failure", async () => {
      mockFetch({ status: 404, body: "Not Found" });

      const result = await searchOfficers({ officerId: "invalid" });

      assert.match(result, /Error \(404\)/);
    });
  });
});
