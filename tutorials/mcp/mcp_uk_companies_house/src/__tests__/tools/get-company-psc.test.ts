import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import getCompanyPsc, { metadata } from "../../tools/get-company-psc";
import { mockFetch } from "./test-helpers";

describe("get-company-psc tool", () => {
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
      assert.equal(metadata.name, "get-company-psc");
    });

    it("should have required MCP annotations", () => {
      assert.equal(metadata.annotations?.readOnlyHint, true);
      assert.equal(metadata.annotations?.destructiveHint, false);
      assert.equal(metadata.annotations?.idempotentHint, true);
    });
  });

  describe("list PSCs mode", () => {
    it("should call /company/{number}/persons-with-significant-control", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await getCompanyPsc({ companyNumber: "12345678" });

      assert.equal(tracker.calls.length, 1);
      assert.equal(
        tracker.urlPath(0),
        "/company/12345678/persons-with-significant-control"
      );
    });

    it("should pass pagination and registerView params", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await getCompanyPsc({
        companyNumber: "12345678",
        itemsPerPage: 10,
        startIndex: 5,
        registerView: "true",
      });

      const params = tracker.queryParams(0);
      assert.equal(params.get("items_per_page"), "10");
      assert.equal(params.get("start_index"), "5");
      assert.equal(params.get("register_view"), "true");
    });

    it("should return formatted JSON on success", async () => {
      const data = { items: [{ name: "John Doe", kind: "individual-person-with-significant-control" }] };
      mockFetch({ status: 200, body: data });

      const result = await getCompanyPsc({ companyNumber: "12345678" });

      assert.equal(result, JSON.stringify(data, null, 2));
    });

    it("should return error on API failure", async () => {
      mockFetch({ status: 401, body: "Unauthorized" });

      const result = await getCompanyPsc({ companyNumber: "12345678" });

      assert.match(result, /Error \(401\)/);
    });

    it("should return error when company not found", async () => {
      mockFetch({ status: 404, body: "Not Found" });

      const result = await getCompanyPsc({ companyNumber: "99999999" });

      assert.match(result, /Error \(404\)/);
    });
  });

  describe("specific PSC mode (pscId + type)", () => {
    it("should call the correct path for individual type", async () => {
      const tracker = mockFetch({ status: 200, body: { name: "John" } });

      await getCompanyPsc({
        companyNumber: "12345678",
        pscId: "psc123",
        type: "individual",
      });

      assert.equal(
        tracker.urlPath(0),
        "/company/12345678/persons-with-significant-control/individual/psc123"
      );
    });

    it("should call the correct path for corporate-entity type", async () => {
      const tracker = mockFetch({ status: 200, body: { name: "Corp" } });

      await getCompanyPsc({
        companyNumber: "12345678",
        pscId: "psc456",
        type: "corporate-entity",
      });

      assert.equal(
        tracker.urlPath(0),
        "/company/12345678/persons-with-significant-control/corporate-entity/psc456"
      );
    });

    it("should call the correct path for individual-beneficial-owner type", async () => {
      const tracker = mockFetch({ status: 200, body: {} });

      await getCompanyPsc({
        companyNumber: "12345678",
        pscId: "psc789",
        type: "individual-beneficial-owner",
      });

      assert.equal(
        tracker.urlPath(0),
        "/company/12345678/persons-with-significant-control/individual-beneficial-owner/psc789"
      );
    });

    it("should call the correct path for legal-person type", async () => {
      const tracker = mockFetch({ status: 200, body: {} });

      await getCompanyPsc({
        companyNumber: "12345678",
        pscId: "psc000",
        type: "legal-person",
      });

      assert.equal(
        tracker.urlPath(0),
        "/company/12345678/persons-with-significant-control/legal-person/psc000"
      );
    });

    it("should return formatted JSON for a specific PSC", async () => {
      const data = { name: "John Doe", kind: "individual-person-with-significant-control" };
      mockFetch({ status: 200, body: data });

      const result = await getCompanyPsc({
        companyNumber: "12345678",
        pscId: "psc123",
        type: "individual",
      });

      assert.equal(result, JSON.stringify(data, null, 2));
    });

    it("should return error when specific PSC not found", async () => {
      mockFetch({ status: 404, body: "Not Found" });

      const result = await getCompanyPsc({
        companyNumber: "12345678",
        pscId: "invalid",
        type: "individual",
      });

      assert.match(result, /Error \(404\)/);
    });

    it("should return error when pscId provided without type", async () => {
      const result = await getCompanyPsc({
        companyNumber: "12345678",
        pscId: "psc123",
      });

      assert.match(result, /Error/);
      assert.match(result, /type/);
    });
  });

  describe("PSC statements mode", () => {
    it("should call persons-with-significant-control-statements (not a sub-path)", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await getCompanyPsc({
        companyNumber: "12345678",
        statements: true,
      });

      assert.equal(tracker.calls.length, 1);
      assert.equal(
        tracker.urlPath(0),
        "/company/12345678/persons-with-significant-control-statements"
      );
    });

    it("should pass pagination params for statements", async () => {
      const tracker = mockFetch({ status: 200, body: { items: [] } });

      await getCompanyPsc({
        companyNumber: "12345678",
        statements: true,
        itemsPerPage: 5,
        startIndex: 0,
      });

      const params = tracker.queryParams(0);
      assert.equal(params.get("items_per_page"), "5");
      assert.equal(params.get("start_index"), "0");
    });

    it("should return formatted JSON for statements", async () => {
      const data = { items: [{ statement: "no-individual-or-entity-with-significant-control" }] };
      mockFetch({ status: 200, body: data });

      const result = await getCompanyPsc({
        companyNumber: "12345678",
        statements: true,
      });

      assert.equal(result, JSON.stringify(data, null, 2));
    });

    it("should return error on statements API failure", async () => {
      mockFetch({ status: 404, body: "Not Found" });

      const result = await getCompanyPsc({
        companyNumber: "99999999",
        statements: true,
      });

      assert.match(result, /Error \(404\)/);
    });

    it("should prefer pscId over statements when both provided", async () => {
      const tracker = mockFetch({ status: 200, body: {} });

      await getCompanyPsc({
        companyNumber: "12345678",
        pscId: "psc123",
        type: "individual",
        statements: true,
      });

      // pscId takes priority — should hit the individual PSC endpoint
      assert.match(tracker.urlPath(0), /individual\/psc123/);
    });
  });
});
