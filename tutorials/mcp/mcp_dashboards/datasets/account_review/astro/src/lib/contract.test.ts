// Unit tests for lib/contract.ts's pure attribute builders — the
// data-unique-* wire contract every list/action binding goes through.
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  callToolAttrs,
  clientRow,
  dataListAttrs,
  kpiRow,
  sendPromptAttrs,
} from "./contract.ts";

test("AI_clientRow_field_emits_data_unique_field", () => {
  assert.deepEqual(clientRow.field("client_name"), { "data-unique-field": "client_name" });
});

test("AI_clientRow_key_emits_data_unique_key", () => {
  assert.deepEqual(clientRow.key("row_id"), { "data-unique-key": "row_id" });
});

test("AI_clientRow_attr_binds_a_row_field_to_a_data_attribute", () => {
  assert.deepEqual(clientRow.attr("data-status", "status"), { "data-unique-attr-data-status": "status" });
});

test("AI_clientRow_attrTemplate_interpolates_field_placeholders", () => {
  assert.deepEqual(clientRow.attrTemplate("href", "#client-{row_id}"), {
    "data-unique-attr-href": "#client-{row_id}",
  });
});

test("AI_kpiRow_field_emits_count_by_tile_bindings", () => {
  assert.deepEqual(kpiRow.field("count"), { "data-unique-field": "count" });
});

test("AI_dataListAttrs_serializes_tool_args_and_poll_interval", () => {
  const attrs = dataListAttrs({
    listName: "clientsLive",
    tool: "list_rows",
    args: { table: "clients", limit: 200 },
  });
  assert.equal(attrs["data-unique-list"], "clientsLive");
  assert.equal(attrs["data-unique-source-tool"], "list_rows");
  assert.deepEqual(JSON.parse(String(attrs["data-unique-source-args"])), { table: "clients", limit: 200 });
  assert.equal(attrs["data-unique-source-path"], "rows");
  assert.equal(attrs["data-unique-source-poll"], 15000);
});

test("AI_callToolAttrs_supports_static_args", () => {
  const attrs = callToolAttrs({
    tool: "reset_from_excel",
    args: {},
    refresh: "clientsLive",
  });
  assert.equal(attrs["data-unique-action"], "callTool");
  assert.equal(attrs["data-unique-source-tool"], "reset_from_excel");
  assert.deepEqual(JSON.parse(String(attrs["data-unique-source-args"])), {});
});

test("AI_callToolAttrs_supports_row_interpolated_argsTemplate", () => {
  const attrs = callToolAttrs({
    tool: "update_row",
    argsTemplate: '{"table":"clients","row_id":{row_id}}',
    refresh: "clientsLive",
  });
  assert.equal(attrs["data-unique-attr-data-unique-source-args"], '{"table":"clients","row_id":{row_id}}');
});

test("AI_sendPromptAttrs_wraps_a_typed_prompt_payload", () => {
  const attrs = sendPromptAttrs("Analyse {client_name} ({client_ref})");
  assert.equal(attrs["data-unique-action"], "sendPrompt");
  assert.deepEqual(JSON.parse(String(attrs["data-unique-attr-data-unique-payload"])), {
    prompt: "Analyse {client_name} ({client_ref})",
  });
});
