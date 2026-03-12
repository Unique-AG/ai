import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import getCompanyOfficers, { metadata } from "../../tools/get-company-officers";
import { mockFetch } from "./test-helpers";

describe("get-company-officers tool", () => {
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
      assert.equal(metadata.name, "get-company-officers");
    });

    it("should have required MCP annotations", () => {
      assert.equal(metadata.annotations?.readOnlyHint, true);
      assert.equal(metadata.annotations?.destructiveHint, false);
      assert.equal(metadata.annotations?.idempotentHint, true);
    });
  });

  describe("list officers mode", () => {
    it("should call /company/{number}/officers", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await getCompanyOfficers({ companyNumber: "12345678" });

      assert.equal(tracker.calls.length, 1);
      assert.equal(tracker.urlPath(0), "/company/12345678/officers");
    });

    it("should pass pagination and filter params", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await getCompanyOfficers({
        companyNumber: "12345678",
        itemsPerPage: 10,
        startIndex: 5,
        registerType: "directors",
        orderBy: "surname",
      });

      const params = tracker.queryParams(0);
      assert.equal(params.get("items_per_page"), "10");
      assert.equal(params.get("start_index"), "5");
      assert.equal(params.get("register_type"), "directors");
      assert.equal(params.get("order_by"), "surname");
    });

    it("should return formatted JSON on success", async () => {
      const data = { items: [{ name: "John Doe" }] };
      mockFetch({ status: 200, body: data });

      const result = await getCompanyOfficers({ companyNumber: "12345678" });

      assert.equal(result, JSON.stringify(data, null, 2));
    });

    it("should pass registerView param", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await getCompanyOfficers({
        companyNumber: "12345678",
        registerType: "directors",
        registerView: "true",
      });

      const params = tracker.queryParams(0);
      assert.equal(params.get("register_type"), "directors");
      assert.equal(params.get("register_view"), "true");
    });

    it("should return error on API failure", async () => {
      mockFetch({ status: 401, body: "Unauthorized" });

      const result = await getCompanyOfficers({ companyNumber: "12345678" });

      assert.match(result, /Error \(401\)/);
    });

    it("should return error when company not found", async () => {
      mockFetch({ status: 404, body: "Not Found" });

      const result = await getCompanyOfficers({ companyNumber: "99999999" });

      assert.match(result, /Error \(404\)/);
    });

    it("should not include undefined optional params in the request", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await getCompanyOfficers({ companyNumber: "12345678" });

      const params = tracker.queryParams(0);
      assert.equal(params.has("items_per_page"), false);
      assert.equal(params.has("start_index"), false);
      assert.equal(params.has("register_type"), false);
      assert.equal(params.has("order_by"), false);
    });
  });

  describe("single appointment mode", () => {
    it("should call /company/{number}/appointments/{id} when appointmentId provided", async () => {
      const tracker = mockFetch({ status: 200, body: { name: "Jane Doe" } });

      await getCompanyOfficers({
        companyNumber: "12345678",
        appointmentId: "abc123",
      });

      assert.equal(tracker.calls.length, 1);
      assert.equal(
        tracker.urlPath(0),
        "/company/12345678/appointments/abc123"
      );
    });

    it("should return error when appointment not found", async () => {
      mockFetch({ status: 404, body: "Not Found" });

      const result = await getCompanyOfficers({
        companyNumber: "12345678",
        appointmentId: "invalid",
      });

      assert.match(result, /Error \(404\)/);
    });
  });
});
