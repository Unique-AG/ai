import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import searchCompanies, { schema, metadata } from "../../tools/search-companies";
import { mockFetch } from "./test-helpers";

describe("search-companies tool", () => {
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
      assert.equal(metadata.name, "search-companies");
    });

    it("should have required MCP annotations", () => {
      assert.equal(metadata.annotations?.readOnlyHint, true);
      assert.equal(metadata.annotations?.destructiveHint, false);
      assert.equal(metadata.annotations?.idempotentHint, true);
      assert.equal(metadata.annotations?.openWorldHint, true);
    });

    it("should have a description", () => {
      assert.ok(metadata.description.length > 0);
    });
  });

  describe("basic search (query provided)", () => {
    it("should call /search/companies with query", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await searchCompanies({ query: "Acme" });

      assert.equal(tracker.calls.length, 1);
      assert.equal(tracker.urlPath(0), "/search/companies");
      assert.equal(tracker.queryParams(0).get("q"), "Acme");
    });

    it("should pass pagination params", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await searchCompanies({
        query: "Acme",
        itemsPerPage: 5,
        startIndex: 10,
      });

      assert.equal(tracker.queryParams(0).get("items_per_page"), "5");
      assert.equal(tracker.queryParams(0).get("start_index"), "10");
    });

    it("should return formatted JSON on success", async () => {
      const mockData = { items: [{ company_name: "ACME LTD" }] };
      mockFetch({ status: 200, body: mockData });

      const result = await searchCompanies({ query: "Acme" });

      assert.equal(result, JSON.stringify(mockData, null, 2));
    });

    it("should return error on API failure", async () => {
      mockFetch({ status: 401, body: "Unauthorized" });

      const result = await searchCompanies({ query: "Acme" });

      assert.match(result, /Error \(401\)/);
    });
  });

  describe("advanced search (no query)", () => {
    it("should call /advanced-search/companies when query is not provided", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await searchCompanies({ companyNameIncludes: "Tech" });

      assert.equal(tracker.calls.length, 1);
      assert.equal(tracker.urlPath(0), "/advanced-search/companies");
      assert.equal(
        tracker.queryParams(0).get("company_name_includes"),
        "Tech"
      );
    });

    it("should map camelCase params to snake_case query params", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await searchCompanies({
        companyNameIncludes: "Tech",
        companyNameExcludes: "Old",
        companyStatus: "active",
        companyType: "ltd",
        incorporatedFrom: "2020-01-01",
        incorporatedTo: "2023-12-31",
        location: "London",
        sicCodes: "62020",
      });

      const params = tracker.queryParams(0);
      assert.equal(params.get("company_name_includes"), "Tech");
      assert.equal(params.get("company_name_excludes"), "Old");
      assert.equal(params.get("company_status"), "active");
      assert.equal(params.get("company_type"), "ltd");
      assert.equal(params.get("incorporated_from"), "2020-01-01");
      assert.equal(params.get("incorporated_to"), "2023-12-31");
      assert.equal(params.get("location"), "London");
      assert.equal(params.get("sic_codes"), "62020");
    });

    it("should map itemsPerPage to 'size' for advanced search", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await searchCompanies({
        companyNameIncludes: "Tech",
        itemsPerPage: 100,
      });

      assert.equal(tracker.queryParams(0).get("size"), "100");
      assert.equal(tracker.queryParams(0).has("items_per_page"), false);
    });

    it("should use basic search when query is provided even with advanced filters", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await searchCompanies({
        query: "Acme",
        companyStatus: "active",
      });

      assert.equal(tracker.urlPath(0), "/search/companies");
    });
  });
});
