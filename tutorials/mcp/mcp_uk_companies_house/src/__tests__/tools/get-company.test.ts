import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import getCompany, { schema, metadata } from "../../tools/get-company";
import { mockFetch, mockResponse } from "./test-helpers";

describe("get-company tool", () => {
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
      assert.equal(metadata.name, "get-company");
    });

    it("should have required MCP annotations", () => {
      assert.equal(metadata.annotations?.readOnlyHint, true);
      assert.equal(metadata.annotations?.destructiveHint, false);
      assert.equal(metadata.annotations?.idempotentHint, true);
    });
  });

  describe("profile only (no include)", () => {
    it("should call /company/{number}", async () => {
      const tracker = mockFetch({ status: 200, body: { company_name: "ACME" } });

      await getCompany({ companyNumber: "12345678" });

      assert.equal(tracker.calls.length, 1);
      assert.equal(tracker.urlPath(0), "/company/12345678");
    });

    it("should return profile wrapped in response object", async () => {
      const profileData = { company_name: "ACME", company_number: "12345678" };
      mockFetch({ status: 200, body: profileData });

      const result = await getCompany({ companyNumber: "12345678" });
      const parsed = JSON.parse(result);

      assert.deepStrictEqual(parsed.profile, profileData);
    });

    it("should return error when company not found", async () => {
      mockFetch({ status: 404, body: "Not Found" });

      const result = await getCompany({ companyNumber: "99999999" });

      assert.match(result, /Error \(404\)/);
    });
  });

  describe("with include sub-resources", () => {
    it("should fetch profile plus sub-resources in parallel", async () => {
      let callCount = 0;
      globalThis.fetch = async (input) => {
        callCount++;
        const url = input as string;
        if (url.includes("/registered-office-address")) {
          return mockResponse(200, { address_line_1: "123 Street" });
        }
        if (url.includes("/insolvency")) {
          return mockResponse(200, { cases: [] });
        }
        return mockResponse(200, { company_name: "ACME" });
      };

      const result = await getCompany({
        companyNumber: "12345678",
        include: ["registered-office-address", "insolvency"],
      });

      // 1 profile + 2 sub-resources
      assert.equal(callCount, 3);

      const parsed = JSON.parse(result);
      assert.deepStrictEqual(parsed.profile, { company_name: "ACME" });
      assert.deepStrictEqual(parsed["registered-office-address"], {
        address_line_1: "123 Street",
      });
      assert.deepStrictEqual(parsed.insolvency, { cases: [] });
    });

    it("should include error for failed sub-resources without failing the whole call", async () => {
      globalThis.fetch = async (input) => {
        const url = input as string;
        if (url.includes("/insolvency")) {
          return mockResponse(404, "Not Found", false);
        }
        return mockResponse(200, { company_name: "ACME" });
      };

      const result = await getCompany({
        companyNumber: "12345678",
        include: ["insolvency"],
      });

      const parsed = JSON.parse(result);
      assert.ok(parsed.profile);
      assert.ok(parsed.insolvency.error);
      assert.match(parsed.insolvency.error, /not found/i);
    });

    it("should short-circuit when profile returns 404", async () => {
      let callCount = 0;
      globalThis.fetch = async () => {
        callCount++;
        return mockResponse(404, "Not Found", false);
      };

      const result = await getCompany({
        companyNumber: "99999999",
        include: ["charges"],
      });

      // Only 1 call (profile), sub-resources skipped
      assert.equal(callCount, 1);
      assert.match(result, /Error \(404\)/);
    });

    it("should handle all three sub-resources", async () => {
      globalThis.fetch = async (input) => {
        const url = input as string;
        if (url.includes("/registered-office-address")) {
          return mockResponse(200, { address: "test" });
        }
        if (url.includes("/insolvency")) {
          return mockResponse(200, { cases: [] });
        }
        if (url.includes("/charges")) {
          return mockResponse(200, { total_count: 0 });
        }
        return mockResponse(200, { company_name: "ACME" });
      };

      const result = await getCompany({
        companyNumber: "12345678",
        include: ["registered-office-address", "insolvency", "charges"],
      });

      const parsed = JSON.parse(result);
      assert.ok(parsed.profile);
      assert.ok(parsed["registered-office-address"]);
      assert.ok(parsed.insolvency);
      assert.ok(parsed.charges);
    });
  });
});
