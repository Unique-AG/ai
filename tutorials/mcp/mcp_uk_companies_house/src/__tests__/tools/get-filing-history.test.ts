import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import getFilingHistory, { schema, metadata } from "../../tools/get-filing-history";
import { mockFetch } from "./test-helpers";

describe("get-filing-history tool", () => {
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
      assert.equal(metadata.name, "get-filing-history");
    });

    it("should have required MCP annotations", () => {
      assert.equal(metadata.annotations?.readOnlyHint, true);
      assert.equal(metadata.annotations?.destructiveHint, false);
      assert.equal(metadata.annotations?.idempotentHint, true);
    });

    it("should have a description", () => {
      assert.ok(metadata.description.length > 0);
    });
  });

  describe("list mode (no transactionId)", () => {
    it("should call /company/{number}/filing-history", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await getFilingHistory({ companyNumber: "12345678" });

      assert.equal(tracker.calls.length, 1);
      assert.equal(tracker.urlPath(0), "/company/12345678/filing-history");
    });

    it("should pass pagination params", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await getFilingHistory({
        companyNumber: "12345678",
        itemsPerPage: 10,
        startIndex: 5,
      });

      const params = tracker.queryParams(0);
      assert.equal(params.get("items_per_page"), "10");
      assert.equal(params.get("start_index"), "5");
    });

    it("should pass category filter", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await getFilingHistory({
        companyNumber: "12345678",
        category: "accounts",
      });

      assert.equal(tracker.queryParams(0).get("category"), "accounts");
    });

    it("should support comma-separated category values", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await getFilingHistory({
        companyNumber: "12345678",
        category: "accounts,confirmation-statement",
      });

      assert.equal(
        tracker.queryParams(0).get("category"),
        "accounts,confirmation-statement"
      );
    });

    it("should return formatted JSON on success", async () => {
      const data = {
        items: [
          { transaction_id: "txn1", type: "AA", date: "2024-01-01" },
        ],
        total_count: 1,
      };
      mockFetch({ status: 200, body: data });

      const result = await getFilingHistory({ companyNumber: "12345678" });

      assert.equal(result, JSON.stringify(data, null, 2));
    });

    it("should return error on API failure", async () => {
      mockFetch({ status: 401, body: "Unauthorized" });

      const result = await getFilingHistory({ companyNumber: "12345678" });

      assert.match(result, /Error \(401\)/);
    });

    it("should return error when company not found", async () => {
      mockFetch({ status: 404, body: "Not Found" });

      const result = await getFilingHistory({ companyNumber: "99999999" });

      assert.match(result, /Error \(404\)/);
    });

    it("should not include undefined optional params in the request", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await getFilingHistory({ companyNumber: "12345678" });

      const params = tracker.queryParams(0);
      assert.equal(params.has("category"), false);
      assert.equal(params.has("items_per_page"), false);
      assert.equal(params.has("start_index"), false);
    });
  });

  describe("single filing mode (transactionId)", () => {
    it("should call /company/{number}/filing-history/{transactionId}", async () => {
      const tracker = mockFetch({
        status: 200,
        body: { transaction_id: "txn123", type: "AA" },
      });

      await getFilingHistory({
        companyNumber: "12345678",
        transactionId: "txn123",
      });

      assert.equal(tracker.calls.length, 1);
      assert.equal(
        tracker.urlPath(0),
        "/company/12345678/filing-history/txn123"
      );
    });

    it("should return formatted JSON for a single filing", async () => {
      const data = {
        transaction_id: "txn123",
        type: "AA",
        date: "2024-06-15",
        description: "accounts-with-accounts-type-full",
      };
      mockFetch({ status: 200, body: data });

      const result = await getFilingHistory({
        companyNumber: "12345678",
        transactionId: "txn123",
      });

      assert.equal(result, JSON.stringify(data, null, 2));
    });

    it("should return error when filing not found", async () => {
      mockFetch({ status: 404, body: "Not Found" });

      const result = await getFilingHistory({
        companyNumber: "12345678",
        transactionId: "invalid",
      });

      assert.match(result, /Error \(404\)/);
    });

    it("should not pass list params when transactionId is provided", async () => {
      const tracker = mockFetch({ status: 200, body: {} });

      await getFilingHistory({
        companyNumber: "12345678",
        transactionId: "txn123",
        category: "accounts",
        itemsPerPage: 10,
        startIndex: 0,
      });

      // Should only hit the single filing endpoint — no query params
      assert.equal(
        tracker.urlPath(0),
        "/company/12345678/filing-history/txn123"
      );
      const params = tracker.queryParams(0);
      assert.equal(params.has("category"), false);
      assert.equal(params.has("items_per_page"), false);
      assert.equal(params.has("start_index"), false);
    });
  });
});
