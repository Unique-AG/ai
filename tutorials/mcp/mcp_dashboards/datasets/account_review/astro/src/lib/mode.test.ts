// Unit tests for lib/mode.ts's mock-data validation.
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { test } from "node:test";
import { mockDataSchema } from "./mode.ts";

test("AI_mockDataSchema_parses_a_clients_table_fixture", () => {
  const mockPath = path.resolve(process.cwd(), "src/data/mock.json");
  const parsed = mockDataSchema.parse(JSON.parse(fs.readFileSync(mockPath, "utf-8")));
  assert.equal(parsed.clients.length, 12);
  assert.equal(parsed.clients[0].identity.name, "Alexander Nesterov");
  assert.equal(parsed.clients[0].figures.documents.length, 3);
});
