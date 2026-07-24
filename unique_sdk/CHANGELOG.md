# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2026.32.0](https://github.com/Unique-AG/ai/compare/unique-sdk-v2026.30.0...unique-sdk-v2026.32.0) (2026-07-24)


### Features

* **cli:** agentic-table read commands (get-sheet, get-cell, cell-history) [UN-22199] ([#2101](https://github.com/Unique-AG/ai/issues/2101)) ([7ac1bc2](https://github.com/Unique-AG/ai/commit/7ac1bc268417e892ba0bd4e0e2dd5d9f6e8db274))
* **sdk:** thread chatId through web-search CLI/SDK to activate node-chat Web Search toggle guard ([#2135](https://github.com/Unique-AG/ai/issues/2135)) ([583c75b](https://github.com/Unique-AG/ai/commit/583c75ba582089e94c469472a32758095bc55b92))
* Token count analytics ([#2112](https://github.com/Unique-AG/ai/issues/2112)) ([f475dc4](https://github.com/Unique-AG/ai/commit/f475dc4606dd723e0fecfcdd09ace2f9c329e960))


### Bug Fixes

* **ai-modules:** improve elicitation skill ([#2145](https://github.com/Unique-AG/ai/issues/2145)) ([599371f](https://github.com/Unique-AG/ai/commit/599371f1d0fb25cdb32234b6b6b336ecb4e44cc2))
* **sdk:** elicit-wait PENDING timeout message must instruct polling again [UN-23181] ([#2113](https://github.com/Unique-AG/ai/issues/2113)) ([848de2d](https://github.com/Unique-AG/ai/commit/848de2d482d0807dd400848a43d311914b0cf688))
* **unique_sdk:** chat-monotonic MCP source numbering and richer citation sources [UN-23199] ([#2131](https://github.com/Unique-AG/ai/issues/2131)) ([81a770d](https://github.com/Unique-AG/ai/commit/81a770d47bc73602fb9449ef3285e47c06daba9f))
* **unique_sdk:** keep crawl-error payloads out of the web-refs manifest [UN-23356] ([#2150](https://github.com/Unique-AG/ai/issues/2150)) ([ea220ff](https://github.com/Unique-AG/ai/commit/ea220ffcb4737ca835bfa618d1f7b890ff2ca2b0))
* **unique_sdk:** UN-23307 redact request payload debug logs by default ([#2143](https://github.com/Unique-AG/ai/issues/2143)) ([30e5886](https://github.com/Unique-AG/ai/commit/30e5886493c223f823b4e9f81bd81b59fcc21a52))


### Miscellaneous

* arm release 2026.32.0 ([6084f04](https://github.com/Unique-AG/ai/commit/6084f0413c8611f1493a00288e4b69797198c3cd))

## [2026.30.0](https://github.com/Unique-AG/ai/compare/unique-sdk-v2026.28.0...unique-sdk-v2026.30.0) (2026-07-17)


### Features

* **agentic-table:** SDK + toolkit wrappers for the public sheet lifecycle (UBP CLI, R1) ([#2052](https://github.com/Unique-AG/ai/issues/2052)) ([6762d3e](https://github.com/Unique-AG/ai/commit/6762d3ec9a87624986e98487640742dba01d2b2a))
* **cli:** split uploaded-search into its own gated skill [UN-21780] ([#1995](https://github.com/Unique-AG/ai/issues/1995)) ([a08b7ee](https://github.com/Unique-AG/ai/commit/a08b7ee11749e582f86241c54f19a6061708feef))
* **mcp:** config-driven reference mapping for MCP list-result citations ([#1994](https://github.com/Unique-AG/ai/issues/1994)) ([e05cb21](https://github.com/Unique-AG/ai/commit/e05cb21f8497b4755e114bfaa84ff1f51b1df0d3))
* **sdk:** record per-item text in MCP refs manifest for citation grounding [UN-22762] ([#2034](https://github.com/Unique-AG/ai/issues/2034)) ([3ee8af2](https://github.com/Unique-AG/ai/commit/3ee8af26bd061fe0cb41c217836712552cb9d2ef))
* **unique_toolkit:** expose per-invocation LLM usage with model identity [UN-20907] (1/3) ([#2051](https://github.com/Unique-AG/ai/issues/2051)) ([9d2d89a](https://github.com/Unique-AG/ai/commit/9d2d89a379e2dcda3833d6fe5eaf4c488a50079b))


### Bug Fixes

* **cli:** resolve message ID from per-turn identity file [UN-22947] ([#2058](https://github.com/Unique-AG/ai/issues/2058)) ([633a66c](https://github.com/Unique-AG/ai/commit/633a66cac81fb9c528e271fa9bd9f758735dab46))
* **sdk:** send explicit scopeIds null for unscoped CLI search [UN-22753] ([#2030](https://github.com/Unique-AG/ai/issues/2030)) ([6768162](https://github.com/Unique-AG/ai/commit/6768162fbb276110569d588f6db34a3e39b0f733))
* **unique_toolkit:** add OVERLAPS/NOT_OVERLAPS UniqueQL operators ([#2028](https://github.com/Unique-AG/ai/issues/2028)) ([bfc33db](https://github.com/Unique-AG/ai/commit/bfc33dbdc8a1d913c1d23c5fe31f15f9fc3bbe29))


### Miscellaneous

* arm release 2026.30.0 ([94e018f](https://github.com/Unique-AG/ai/commit/94e018fa010fb5a0ffd8f449cf078c604b7c12ee))

## [2026.28.0](https://github.com/Unique-AG/ai/compare/unique-sdk-v2026.26.0...unique-sdk-v2026.28.0) (2026-07-03)


### Features

* carry MCP reference enrichment fields end to end [UN-22310] ([#1953](https://github.com/Unique-AG/ai/issues/1953)) ([ea4c147](https://github.com/Unique-AG/ai/commit/ea4c1477137fa01ee7c7f6ebc7043cbec37abdd8))
* **cli:** browser steering command (unique-cli browser) ([#1986](https://github.com/Unique-AG/ai/issues/1986)) ([cf3e855](https://github.com/Unique-AG/ai/commit/cf3e8550e6e9f99393dd72f1c183223e682e105a))
* **cli:** per-task uploaded documents via uploaded-search [UN-21780] ([#1965](https://github.com/Unique-AG/ai/issues/1965)) ([e91c2a7](https://github.com/Unique-AG/ai/commit/e91c2a7c1483987cfb7ed4a56a38dd53f3cdfbbd))
* **cli:** scope read/cite/ls/download to per-message metadata filter (UN-21780) ([#1868](https://github.com/Unique-AG/ai/issues/1868)) ([982ef65](https://github.com/Unique-AG/ai/commit/982ef651a4a574ff5aff3ffabb915698fc9ea124))
* **cli:** share record_mcp_citations for tools-mode MCP referencing [UN-22484] ([#1972](https://github.com/Unique-AG/ai/issues/1972)) ([9e8c4be](https://github.com/Unique-AG/ai/commit/9e8c4bea080cf6e5efe5b826c1f807648c35278e))
* **dci:** cite read-method taxonomy + multimodal hallucination context [UN-21765] ([#1895](https://github.com/Unique-AG/ai/issues/1895)) ([b02fdcb](https://github.com/Unique-AG/ai/commit/b02fdcb7eb3b625a9f8da4f006b548428d048542))
* **mcp:** reference + groundedness support for MCP tool results ([#1896](https://github.com/Unique-AG/ai/issues/1896)) ([84eb29d](https://github.com/Unique-AG/ai/commit/84eb29d309880fdf887be48902a77b46c587287e))
* **sdk, toolkit:** allow segment_kind on message modify (UN-22153) ([#1992](https://github.com/Unique-AG/ai/issues/1992)) ([4c62b84](https://github.com/Unique-AG/ai/commit/4c62b84b68f61966784365be1744f564a9e53859))
* **sdk:** autoapprove elicitation ([#1940](https://github.com/Unique-AG/ai/issues/1940)) ([6b36cc7](https://github.com/Unique-AG/ai/commit/6b36cc7f9285f72af4b77c86947834c908d95162))
* **sdk:** forward chatId/spaceId headers on browser bridge calls ([#1996](https://github.com/Unique-AG/ai/issues/1996)) ([9a3a792](https://github.com/Unique-AG/ai/commit/9a3a792f2c6b7cfa1fcfb32e09a63f37d807f619))
* **sdk:** move folder api ([#1897](https://github.com/Unique-AG/ai/issues/1897)) ([6ea7d02](https://github.com/Unique-AG/ai/commit/6ea7d02ebc4b7f6d7581466948a80258c438af78))
* **sdk:** sub-agents ([#1926](https://github.com/Unique-AG/ai/issues/1926)) ([6255e50](https://github.com/Unique-AG/ai/commit/6255e50fd2f93bf309e149cd498135efd9e75904))
* **toolkit:** add segment_kind/response_turn_id params to create_assistant_message_async [UN-22064] ([#1948](https://github.com/Unique-AG/ai/issues/1948)) ([6784095](https://github.com/Unique-AG/ai/commit/6784095781676a034a4d0020b669e366f397e4e6))
* **uqadm:** wire assistantPrompts through upsert and migrate [UN-22129] ([#1903](https://github.com/Unique-AG/ai/issues/1903)) ([eb78043](https://github.com/Unique-AG/ai/commit/eb7804328152458a4e6bc10ff744c6577fc0d195))


### Bug Fixes

* **cli:** file upload ([#1924](https://github.com/Unique-AG/ai/issues/1924)) ([ac86b3b](https://github.com/Unique-AG/ai/commit/ac86b3b7dc72cfc2d1a86c51342f002f72199bc5))
* **uqadm:** migrate user model selection settings [UN-22297] ([#1943](https://github.com/Unique-AG/ai/issues/1943)) ([d31d637](https://github.com/Unique-AG/ai/commit/d31d637c2d854f93e878ecd1f20b5b92489fbc90))


### Miscellaneous

* arm release 2026.28.0 ([e890f5e](https://github.com/Unique-AG/ai/commit/e890f5ecc6217d885dbdb4a3d6f093237320e1bd))

## [2026.26.0](https://github.com/Unique-AG/ai/compare/unique-sdk-v2026.24.0...unique-sdk-v2026.26.0) (2026-06-22)


### Features

* **cli:** add page-range filtering to unique-cli read ([#1847](https://github.com/Unique-AG/ai/issues/1847)) ([aba3d50](https://github.com/Unique-AG/ai/commit/aba3d50a4486e91892ef1de7253e78fef516ce4a))
* **cli:** add unique-cli read command for indexed chunk retrieval ([#1833](https://github.com/Unique-AG/ai/issues/1833)) ([43d4367](https://github.com/Unique-AG/ai/commit/43d4367a43eaaf9bb580d7a0e33028dd386b4bd4))
* **sdk:** add chat_id parameter to update_content function ([#1861](https://github.com/Unique-AG/ai/issues/1861)) ([66f537b](https://github.com/Unique-AG/ai/commit/66f537b112024a86c90ca4fb8ab21fbb0957dbc8))
* **sdk:** add scopeToAssignedRows for magic table sheet reads ([#1808](https://github.com/Unique-AG/ai/issues/1808)) ([c7c4bc9](https://github.com/Unique-AG/ai/commit/c7c4bc9ef32ae210becdce71d150ce2e30699eb0))
* **unique_sdk:** add dynamic frontend CLI support ([#1837](https://github.com/Unique-AG/ai/issues/1837)) ([5624ccb](https://github.com/Unique-AG/ai/commit/5624ccb3badc1637a6f54a60012e17a11878be75))
* **unique-sdk-cli:** add dynamic frontend delete ([#1873](https://github.com/Unique-AG/ai/issues/1873)) ([3db8e8a](https://github.com/Unique-AG/ai/commit/3db8e8aa91c57c342454b360b862ff9e15671e38))
* **unique-sdk-cli:** support versioned file uploads ([#1840](https://github.com/Unique-AG/ai/issues/1840)) ([9adc16c](https://github.com/Unique-AG/ai/commit/9adc16cff70bf3a52dd06b65d8ac08486eb25163))
* **unique-sdk-cli:** surface dynamic frontend view and config/share urls ([#1871](https://github.com/Unique-AG/ai/issues/1871)) ([0cc434c](https://github.com/Unique-AG/ai/commit/0cc434c93c7183765e11f2d2fe64fb22cbb86935))


### Bug Fixes

* **sdk:** filter nullable request headers ([#1906](https://github.com/Unique-AG/ai/issues/1906)) ([8d20580](https://github.com/Unique-AG/ai/commit/8d20580f2a3e0aff5d1915f5597e2a71e1efad16))
* **sdk:** omit versioningEnabled when None on file upload ([#1857](https://github.com/Unique-AG/ai/issues/1857)) ([a2203a5](https://github.com/Unique-AG/ai/commit/a2203a56b19201809f0d932ed726fea622752594))
* **unique-sdk-cli:** extend elicitation wait timeout ([#1853](https://github.com/Unique-AG/ai/issues/1853)) ([e1d3b30](https://github.com/Unique-AG/ai/commit/e1d3b3044b39f3da49a59e98b9acd5596a4998a6))
* **unique-sdk-cli:** include dynamic frontend space urls ([#1869](https://github.com/Unique-AG/ai/issues/1869)) ([6cb86b1](https://github.com/Unique-AG/ai/commit/6cb86b1a1ded8a552dd9f264eb4bc028196d8b5a))


### Miscellaneous

* arm release 2026.26.0 ([d3c79b3](https://github.com/Unique-AG/ai/commit/d3c79b385f2714ab9c6237a545da21dea0cfb34a))

## [2026.24.0](https://github.com/Unique-AG/ai/compare/unique-sdk-v2026.22.0...unique-sdk-v2026.24.0) (2026-06-04)


### Features

* **cli:** add unique-cli cite command for file page citation declarations [UN-21284] ([#1774](https://github.com/Unique-AG/ai/issues/1774)) ([2d46309](https://github.com/Unique-AG/ai/commit/2d46309a8aec2f68650932b76dd2fcec087ecc94))
* include subagent into conduct ([#1740](https://github.com/Unique-AG/ai/issues/1740)) ([3d4faae](https://github.com/Unique-AG/ai/commit/3d4faaef05729f44acee7c4acf06e610a2dbe8c3))
* **unique-toolkit:** allow sub-agents to take orchestrator control ([#1737](https://github.com/Unique-AG/ai/issues/1737)) ([cd711ce](https://github.com/Unique-AG/ai/commit/cd711ced727dc1f1c3440274c141da4b24337ad7))
* **web-search:** add citation manifest support ([#1733](https://github.com/Unique-AG/ai/issues/1733)) ([230b3d4](https://github.com/Unique-AG/ai/commit/230b3d4ee7bb4cfc1369b695e0cbbabac4908832))


### Bug Fixes

* remove empty bearer in header for httpx cli calls ([#1747](https://github.com/Unique-AG/ai/issues/1747)) ([9915515](https://github.com/Unique-AG/ai/commit/9915515ff830d58e0e9a653caaf367b58eef01a2))
* **short-term-memory:** return None instead of crashing on empty SDK response ([#1730](https://github.com/Unique-AG/ai/issues/1730)) ([3fa5bc0](https://github.com/Unique-AG/ai/commit/3fa5bc0e33d50dca26792eed5652409d695a03e7))


### Miscellaneous

* arm release 2026.24.0 ([2b3ff5d](https://github.com/Unique-AG/ai/commit/2b3ff5d2e13c4c98cd0012f0306db10f980aa886))

## [2026.22.0](https://github.com/Unique-AG/ai/compare/unique-sdk-v2026.20.0...unique-sdk-v2026.22.0) (2026-05-21)


### Bug Fixes

* **security:** address Dependabot pillow alerts and CodeQL finding ([#1617](https://github.com/Unique-AG/ai/issues/1617)) ([6e49fcb](https://github.com/Unique-AG/ai/commit/6e49fcbf59fd6e93e36326869038b1f89f4c23d0))


### Miscellaneous

* arm release 2026.22.0 ([3fe07bd](https://github.com/Unique-AG/ai/commit/3fe07bdafc85a45f8275a18b72f6ebe766c15464))

## [2026.20.0](https://github.com/Unique-AG/ai/compare/unique-sdk-v2026.18.0...unique-sdk-v2026.20.0) (2026-05-08)


### Features

* **sdk:** Add Analytics Order API and run utility ([#1503](https://github.com/Unique-AG/ai/issues/1503)) ([01f37aa](https://github.com/Unique-AG/ai/commit/01f37aa3666b66a19cb22a5636c734f57a1d0f17))
* **sdk:** add missing docs ([#1500](https://github.com/Unique-AG/ai/issues/1500)) ([73c0dcd](https://github.com/Unique-AG/ai/commit/73c0dcd7d37deb36a55d1483f64e6ae09fdb9df5))
* **sdk:** Add Module API resource for managing assistant modules ([#1471](https://github.com/Unique-AG/ai/issues/1471)) ([b376a1d](https://github.com/Unique-AG/ai/commit/b376a1d460d52f2d34181dda801fa63111b43909))
* **sdk:** add WebSearch / WebCrawl resources and unique-cli web-search ([#1611](https://github.com/Unique-AG/ai/issues/1611)) ([2cc2fab](https://github.com/Unique-AG/ai/commit/2cc2fab0c3e19806c1797ae7b169fd71acee35e4))
* **sdk:** allow download_content to write to caller-specified target_path ([#1585](https://github.com/Unique-AG/ai/issues/1585)) ([df57cc9](https://github.com/Unique-AG/ai/commit/df57cc9610d7065fd0292a6b4211406d37c3e89c))
* **sdk:** Briefing API resource and PUT HTTP support ([#1574](https://github.com/Unique-AG/ai/issues/1574)) ([23455e7](https://github.com/Unique-AG/ai/commit/23455e7e90792767b41e43122230b52f6ef12975))
* **sdk:** rewrite blob upload URLs via INGESTION_UPLOAD_API_URL_INTERNAL ([#1588](https://github.com/Unique-AG/ai/issues/1588)) ([5783fb5](https://github.com/Unique-AG/ai/commit/5783fb5c4d4053ed83a505ce75b3ca271d8d1757))
* **unique-sdk:** derive preview-PDF blob name from content id ([#1532](https://github.com/Unique-AG/ai/issues/1532)) ([d36d130](https://github.com/Unique-AG/ai/commit/d36d130e6c38f781d767c2a53c6bf2ac933c1ccc))
* **unique-skill:** including skill choices to payload ([#1636](https://github.com/Unique-AG/ai/issues/1636)) ([36e8275](https://github.com/Unique-AG/ai/commit/36e82750e89d350e2293b8144035bac903829445))


### Bug Fixes

* **cli:** enforce .unique-search.json scope across search, ls, and write ops ([#1627](https://github.com/Unique-AG/ai/issues/1627)) ([7f0e6ee](https://github.com/Unique-AG/ai/commit/7f0e6eeeb2f67e8cf6ecc131110bc6287755b9b8))


### Miscellaneous

* arm release 2026.20.0 ([#1506](https://github.com/Unique-AG/ai/issues/1506)) ([0820dc9](https://github.com/Unique-AG/ai/commit/0820dc9a1c661470c2ef44ed2eed6830b508ca8d))

## [2026.18.0](https://github.com/Unique-AG/ai/compare/unique-sdk-v0.11.12...unique-sdk-v2026.18.0) (2026-04-23)


### Miscellaneous

* arm release 2026.18.0 ([#1493](https://github.com/Unique-AG/ai/issues/1493)) ([bc435b2](https://github.com/Unique-AG/ai/commit/bc435b2c5838a9e16484fb054beb277b8262c136))

## [0.11.12] - 2026-04-22
- `AgenticTable.GetSheetData`: add `includeSheetMetadata` and `includeRowMetadata` (optional GET query params; `includeRowMetadata` for `GET /magic-table/{tableId}` aligns with in-flight public API work)
- Align other `AgenticTable` request/response types with the public magic-table REST contract (`2023-12-06` / `node-chat`): `RowVerificationStatus` uses `NEEDS_REVIEW` to match `MagicTableRowStatus`; `MagicTableAction` adds `InsertRow` and `GenerateOverview`; `bulk_update_status` adds optional `locked`; `SetArtifact` optional `name`/`mimeType` and `MagicTableArtifactType` including `AGENTIC_REPORT`; `set_activity` returns `MagicTableActivityResponse`, `set_artifact` returns `ColumnMetadataUpdateStatus`; extend cell/sheet TypedDicts (`metaData`, `rowMetadata`, `magicTableSheetMetadata`, optional `chatId` / `magicTableRowCount`); export `AgenticTableCellMetaData`, `MagicTableActivityResponse`, `MagicTableArtifactType`, `MagicTableMetadataEntry`
- Docs: update `agentic_table` reference for the above; add test coverage for `includeSheetMetadata` / `includeRowMetadata` on `get_sheet_data`

## [0.11.11] - 2026-04-22
- Add `Space.get_spaces` / `Space.get_spaces_async` to list spaces with optional name filter and skip/take pagination

## [0.11.10] - 2026-04-21
- Fix `unique-cli mcp` crashing with `AttributeError: isError` on spec-compliant `CallToolResult` responses that only include `content`. `format_mcp_response` now reads `isError`, `name`, and `mcpServerId` defensively via `getattr(..., default)` and accepts a keyword-only `tool_name` fallback so the header stays informative when the server omits `name`
- `cmd_mcp` now threads the parsed payload name into `format_mcp_response` and wraps the final format step in a defensive `try/except` that prints the raw response payload instead of a traceback if the formatter ever errors
- Mark `MCP.isError`, `MCP.name`, `MCP.mcpServerId` as `NotRequired` on the response type to match the MCP spec and the Unique backend's observed behaviour (typing-only change)

## [0.11.9] - 2026-04-21
- Docs: update the `unique-cli-elicitation` skill to require both `--chat-id "$UNIQUE_CHAT_ID"` and `--message-id "$UNIQUE_MESSAGE_ID"` on every `elicit ask` call, explain that every elicitation is anchored to a `(chatId, messageId)` pair in the backend, and document the two new env vars agents should always forward

## [0.11.8] - 2026-04-21
- Workaround for UN-19815: `elicit ask` / `elicit create` now wrap the elicitation in a short-lived placeholder "thinking" timeline (a placeholder `ASSISTANT` message + a `RUNNING` `MessageLog` step) so the chat UI actually renders the elicitation while it is pending. The placeholder is torn down automatically (collapsed or deleted) when the user responds, on timeout, on API error, or on Ctrl-C
- Add `--visible` / `--no-visible`, `--assistant-id`, `--placeholder-text`, `--cleanup` flags to `elicit ask` and `elicit create` in both the one-shot CLI and the REPL shell. The workaround is enabled by default whenever `--chat-id` is passed and `--message-id` is not; pass `--no-visible` to opt out once the UN-19815 UI fix lands
- `elicit wait` and `elicit respond` now auto-clean any placeholder a prior `elicit create --visible` left behind, by reading the placeholder ids back from the elicitation's `metadata`
- Serialize `completedAt` as an ISO-8601 UTC string (not a raw `datetime`) when collapsing the visibility placeholder via `Message.modify`, so the `PATCH /messages/{id}` body is accepted by the backend; without this the placeholder would stay visually "running" after the user responded
- Fix `elicit pending` crashing with `AttributeError: 'list' object has no attribute 'get'` — the backend returns a raw JSON array; both list and dict shapes are now accepted
- Fix `elicit wait` / `elicit ask` never terminating when the user answers — `ACCEPTED` and `REJECTED` are now recognised as terminal statuses alongside `RESPONDED` / `DECLINED` / `CANCELLED` / `EXPIRED` / `COMPLETED`
- Accept `REJECT` as a valid `elicit respond --action` value (forwarded to the backend as `REJECT`)
- Update the `unique-cli-elicitation` skill and the CLI docs page with the new flags and a note on when to turn the workaround off

## [0.11.7] - 2026-04-20
- Chore: exempt `unique-sdk` from the workspace root `exclude-newer` cutoff so recent SDK releases resolve correctly under `UV_NO_SOURCES=1`

## [0.11.6] - 2026-04-20
- Add `mimeType` field to `Content`

## [0.11.5] - 2026-04-16
- Add `elicit` CLI command group with `ask`, `create`, `pending`, `get`, `wait`, `respond` subcommands for both one-shot and interactive REPL modes, wrapping the existing `Elicitation` API resource
- Add `elicit ask` convenience command that creates a FORM elicitation and blocks until the user responds, declines, cancels, or the request expires
- Add formatting helpers for elicitation display (detail view, pending list, response result)
- Add agent skill for elicitation (`unique-cli-elicitation`) so agents route user-facing questions through the platform UI instead of asking in plain chat
- Add `CLI > Elicitation` documentation page and expose it in the mkdocs nav

## [0.11.4] - 2026-04-15
- Chore: standardize pytest configuration across workspace packages

## [0.11.3] - 2026-04-14
- Make `UNIQUE_API_KEY` and `UNIQUE_APP_ID` optional in the CLI — not needed on localhost or in a secured cluster

## [0.11.2] - 2026-04-14
- Chore: add `importlib` import mode to pytest config to prevent namespace collisions
- Chore: update `exclude-newer-package` timestamps and lockfile refresh

## [0.11.1] - 2026-04-09
- Fix stack trace exposure in custom-assistant example: return generic error messages instead of `str(e)` in HTTP responses

## [0.11.0] - 2026-04-09
- Widen `openai` dependency upper bound from `<2` to `<3` to allow openai SDK v2.x (required for litellm security fix)

## [0.10.101] - 2026-04-06
- Fix all `async def` methods in `AgenticTable` that incorrectly called synchronous `_static_request` instead of `await _static_request_async`, blocking the event loop
- Fix `wait_for_ingestion_completion` to use `Content.search_async` instead of synchronous `Content.search`

## [0.10.100] - 2026-04-06
- Fix `Integrated.responses_stream_async` blocking the asyncio event loop by calling synchronous `_static_request` instead of `await _static_request_async` — concurrent coroutines (STM lookups, file downloads, other API calls) were starved for 60-75s per LLM call

## [0.10.99] - 2026-04-02
- Add `ScheduledTask` API resource with full CRUD operations (create, list, retrieve, modify, delete) and async variants
- Add `schedule` CLI command group with `list`, `get`, `create`, `update`, `delete` subcommands for both one-shot and interactive REPL modes
- Add formatting helpers for scheduled task display (detail view and table view)
- Add agent skill for scheduled task management (`unique-cli-scheduled-tasks`)

## [0.10.98] - 2026-04-02
- Chore: migrate to uv workspace; switch local dependency sources from path-based to workspace references

## [0.10.97] - 2026-04-01
- Chore: uv `exclude-newer` (2 weeks) and lockfile refresh

## [0.10.96] - 2026-03-31
- Remove leftover `poetry` references from tox config, CONTRIBUTING.md, and tutorial docs — all replaced with `uv` equivalents

## [0.10.95] - 2026-03-30
- Add `mcp` command to the CLI for calling MCP server tools directly via JSON payload
- Support inline JSON, `--file`, and `--stdin` input modes for MCP tool payloads
- Add Claude Code skill for CLI MCP tool calls (`unique-cli-mcp`)

## [0.10.94] - 2026-03-30
- Add `Benchmarking` functions and script.

## [0.10.93] - 2026-03-25
- Add `Space.create_chat`

## [0.10.92] - 2026-03-19
- Add experimental CLI (`unique-cli`) for interactive file exploration of the Unique knowledge base
- Add `click` as a required dependency for the CLI
- Add Claude Code skills for CLI file management and search

## [0.10.91] - 2026-03-17
- Chore: switch basedpyright to `recommended` mode with zero errors/warnings
- Refactor: replace deprecated `typing` aliases (`Optional`, `List`, `Dict`, `Type`, `typing.Mapping`, `typing.Iterator`) with modern PEP 585/604 equivalents
- Refactor: rename `_ApiVersion` → `ApiVersion`; use `inspect.iscoroutinefunction` instead of deprecated `asyncio.iscoroutinefunction`
- Fix: use `list_result.data` instead of dict-key access in `chat_history` to access typed `ListObject` response

## [0.10.90] - 2026-03-17
- Add `qdrantParams` to `Search.create` for configuring Qdrant search parameters (hnsw_ef, exact, quantization, consistency)

## [0.10.89] - 2026-03-16
- Add `usage: Integrated.Usage | None` field to `ResponsesStreamResult` TypedDict (UN-18040)

## [0.10.88] - 2026-03-12
- Add `MessageTool` API resource for node-chat `POST/GET /messages/tools` (batch create and get by messageIds). Enables toolkit and orchestrator to persist and load tool calls via a dedicated table.

## [0.10.87] - 2026-03-12
- Fix: resolve non-breaking basedpyright errors; modern typing in core modules (`__init__`, `_api_requestor`, `_http_client`)
- Fix: restore strict key access in `AgenticTable.set_multiple_cells` so missing required fields raise `ValueError` instead of silently defaulting (UN-17995)

## [0.10.86] - 2026-03-12
- Fix return type for `Integrated.chat_stream_completion` and `Integrated.chat_stream_completion_async` to correctly reflect `StreamCompletionResult` (message, toolCalls, usage) instead of `Message`

## [0.10.85] - 2026-03-10
- Examples: migrate custom-assistant from Poetry to uv with `src/` layout
- Examples: replace hardcoded credentials in custom-assistant with `os.getenv()` for env-based configuration
- Examples: fix Ollama import (`langchain.llms` → `langchain_community.llms`) and add langchain dependencies

## [0.10.84] - 2026-03-03
- Build: migrate from Poetry to uv (PEP 621 `pyproject.toml`, `uv.lock`)

## [0.10.83] - 2026-02-28
- Add `Space.update` method to update a space (assistant) configuration

## [0.10.82] - 2026-02-13
- Add `User.get_by_id` method to retrieve a user by their ID

## [0.10.81] - 2026-02-13
- Add documentation versioning support using `mike`
- Add versioned documentation build and deploy workflows

## [0.10.80] - 2026-02-12
- Add support for creating folders by scope using `parentScopeId` and `relativePaths` parameters in `Folder.create_paths`

## [0.10.79] - 2026-02-05
- Add update_ingestion_state function to update content ingestion state.

## [0.10.78] - 2026-02-05
- Internal Improvements.

## [0.10.77] - 2026-02-05
- Add `RERUN_ROW` action to `MagicTableAction` enum for targeted row re-execution in Agentic Tables

## [0.10.76] - 2026-02-05
- Use literals for action source and mode in Elicitation for better API clarity

## [0.10.75] - 2026-02-02
- Add correlation parameter to Message.create for linking messages to parent messages in other chats.
- Add correlation parameter to Space.create_message and send_message_and_wait_for_completion utility.

## [0.10.74] - 2026-01-22
- Add delete space function.

## [0.10.73] - 2026-01-21
- added searchtype `FULL_TEXT` and `POSTGRES_FULL_TEXT`

## [0.10.72] - 2026-01-20
- Expose elicitation functions [BETA feature].

## [0.10.71] - 2026-01-16
- Add local CI testing commands via poethepoet (poe lint, poe test, poe ci-typecheck, etc.)

## [0.10.70] - 2026-01-16
- Adding additional parameters `isQueueable`, `executionOptions` and `progressTitle` to the message execution

## [0.10.69] - 2026-01-16
- Add unified type checking CI with basedpyright

## [0.10.68] - 2026-01-14
- Add missing direct dependencies (httpx, anyio, aiohttp, regex, tiktoken) for deptry compliance

## [0.10.67] - 2026-01-14
- chore(deps): bump requests from 2.31.0 to 2.32.4 in examples/custom-assistant

## [0.10.66] - 2026-01-05
- Expose appliedIngestionConfig field on content search.

## [0.10.65] - 2026-01-05
- Add new params for elicitation to `call_tool` api

## [0.10.64] - 2025-12-31
- Add create path functionality to theupsert function and allow getinfo(s) to query by parentfolderpath.

## [0.10.63] - 2025-12-23
- Add functions to create a space and manage its access.

## [0.10.62] - 2025-12-23
- Add get user groups function and allow the get users function to filter by username.

## [0.10.61] - 2025-12-22
- Add `displayInChat` field to ingestion config, allowing silent uploads to chat.

## [0.10.60] - 2025-12-19
- Expose startedStreamingAt and gptRequest fields

## [0.10.59] - 2025-12-19
- Add context field to MagicTableSheetIngestParams.
- Add rowMetadata and context fields to MagicTableRow.

## [0.10.58] - 2025-12-16
- chore(deps): Bump urllib3 from 2.5.0 to 2.6.2

## [0.10.57] - 2025-12-06
- Add description field on create chat completions params.

## [0.10.56] - 2025-12-05
- Add description field on create chat completions params.

## [0.10.55] - 2025-12-04
- Allow configuring inherit access on folder creation.

## [0.10.54] - 2025-12-02
- Add types for Agentic Table api methods.

## [0.10.53] - 2025-12-01
- Improve OpenAI Proxy docs https://unique-ag.github.io/ai/unique-sdk/

## [0.10.52] - 2025-11-21
- Centralized docs to https://unique-ag.github.io/ai/unique-sdk/

## [0.10.51] - 2025-11-21
- Add function to get a space.

## [0.10.50] - 2025-11-21
- Allow updating the configuration of a user and group.

## [0.10.49] - 2025-11-21
- Add get folder by scope id function

## [0.10.48] - 2025-11-20
- Update Agentic Table LogDetail and LogEntry types.

## [0.10.47] - 2025-11-19
- Add expired/s at fields on content search result.

## [0.10.46] - 2025-11-18
- chat_against_file function allows now a should_delete_chat flag.

## [0.10.45] - 2025-11-18
- Create group and manage users functions.

## [0.10.44] - 2025-11-18
- add function to get all messages in a chat.

## [0.10.43] - 2025-11-14
- Add get, delete and update groups functions.

## [0.10.42] - 2025-11-14
- Add get_users function.

## [0.10.41] - 2025-11-13
- Add create_message and get_latest_message.

## [0.10.40] - 2025-11-10
- Don't send description if not defined.

## [0.10.39] - 2025-11-07
- Add function to get llm models

## [0.10.38] - 2025-11-06
- Add description property to Reference and Content.

## [0.10.37] - 2025-11-04
- Introduce local integration tests for Content API Resource

## [0.10.36] - 2025-11-04
- Introduce local integration tests for Folder API Resource

## [0.10.35] - 2025-11-04
- Inmprove folder get infos types.

## [0.10.34] - 2025-10-29
- Add documentation for agentic table.

## [0.10.33] - 2025-10-27
- Improve messagelog and message execution types.

## [0.10.32] - 2025-10-14
- Add function to stream to chat frontend.

## [0.10.31] - 2025-10-13
- Add readme for message log and execution.

## [0.10.30] - 2025-10-07
- Improve types for content get infos.

## [0.10.29] - 2025-10-06
- Switch default model used from `GPT-3.5-turbo (0125)` to `GPT-4o (1120)`

## [0.10.28] - 2025-10-03
- Use non blocking versions of `Space.get_latest_message` and `Message.retrieve` in `send_message_and_wait_for_completion`.

## [0.10.27] - 2025-09-24
- Improve readme to use Unique AI.

## [0.10.26] - 2025-09-22
- Improve typing.

## [0.10.25] - 2025-09-18
- Add support for udpate and delete files by file or folder path.

## [0.10.24] - 2025-09-17
- Add function to update a folder.

## [0.10.23] - 2025-09-12
- Revert to using default reasoning effort.

## [0.10.22] - 2025-09-12
- Add support for metadata update of a file.

## [0.10.21] - 2025-09-04
- Update Chat Completions API types and add support for reasoning effort.

## [0.10.20] - 2025-09-04
- Update Responses API types

## [0.10.19] - 2025-09-02
- Improve `send_message_and_wait_for_completion`:
    - Add option to select stop_condition `["stoppedStreamingAt", "completedAt"]`. 
    - Load `debugInfo` from `last_user_message` for better developer experience.

## [0.10.18] - 2025-09-02
- Temporarily remove support for update and delete files by filePath.

## [0.10.17] - 2025-09-01
- Add function to update a file

## [0.10.16] - 2025-08-31
- Add function to delete a content.

## [0.10.15] - 2025-08-28
- Add default values for message log types

## [0.10.14] - 2025-08-28
- Add function to delete folders and files recursively

## [0.10.13] - 2025-08-24
- Add functions to create, get and update a message eecution and create and update a message log.

## [0.10.12] - 2025-08-24
- Switch to using Content get info deprecated endpoint to make sure we support older release versions.

## [0.10.11] - 2025-08-24
- Enforce usage of ruff using pipeline

## [0.10.10] - 2025-08-18
- Fix wrong name of references in `Space.Message`. 
- Fix wrong name of assessment in `Space.Message`.
- Remove default values for `text`, `originalText` and `debugInfo` in `Space.Message` as these don't have an effect.

## [0.10.9] - 2025-08-15
- Add script to wait for content ingestion finished.

## [0.10.8] - 2025-08-13
- Add support for Agentic Table.

## [0.10.7] - 2025-08-13
- Make metadata optional when uploading a file.

## [0.10.6] - 2025-08-06
- Make tools optional for running an agent.

## [0.10.5] - 2025-08-06
- Get paginated files and folders info.

## [0.10.4] - 2025-08-05
- Add support for reasoning API with streaming within a chat.

## [0.10.3] - 2025-08-05
- Expose scoreThreshold param for search.

## [0.10.2] - 2025-08-05
- Add script to chat against file.

## [0.10.1] - 2025-08-05
- Allow deletion of a space chat.

## [0.10.0] - 2025-08-04
- Add MCP support

## [0.9.42] - 2025-07-31
- Fix wrong chat in space example.

## [0.9.41] - 2025-07-31
- Fix double-slash error in open ai proxy script.

## [0.9.40] - 2025-07-22
- Fixed bug where get requests send body with the request. This is not allowed by WAF policies.

## [0.9.39] - 2025-07-18
- Add script to chat in a space.

## [0.9.38] - 2025-07-18
- [Experimental] Add support for Unique OpenAI proxy. You can now use the OpenAI SDK directly through Unique. Checkout how to do this and a few examples here: `tutorials/unique_basics/sdk_examples/openai_scripts.py`.

## [0.9.37] - 2025-07-10
- Add `sheetName` property to the `MagicTableSheetIngestParams` object used by function that ingests magic table sheets.

## [0.9.36] - 2025-06-23
- Allow passing a user id when creating chat completions. This is optional and it does not impact the current behaviour.

## [0.9.35] - 2025-06-18
- Allow scope access updates (add/remove) on folder based on scope id or path.

## [0.9.34] - 2025-06-17
- Allow ingestion config updates on folder based on scope id or path.

## [0.9.33] - 2025-06-11
- Add function to get a folder by id or by path.

## [0.9.32] - 2025-06-11
- Add function to ingest magic table sheets.

## [0.9.31] - 2025-05-21
- Add function to update folder access (add or remove).

## [0.9.30] - 2025-05-21
- Add function to update folder ingestion config.

## [0.9.29] - 2025-05-20
- Add function to create folder paths if they do not exist.

## [0.9.28] - 2025-05-20
- Add function to search content info. This also allows filtering content info by metadata info.

## [0.9.27] - 2025-05-14
- Add the possibility to specify metadata when creating or updating a Content.

## [0.9.26] - 2025-05-13
- Add the possibility to specify ingestionConfig when creating or updating a Content.

## [0.9.25] - 2025-05-02
- Fixed typos in `README.md`, including incorrect `sdk.utils` imports and code example errors.

## [0.9.24] - 2025-04-23
- Make `chatId` property in `Search.CreateParams` optional

## [0.9.23] - 2025-03-25
- Define programming language classifier explicitly for python 3.11

## [0.9.22] - 2025-02-25
- update the retry_on_error to only `APIError` and `APIConnectionError` update the `resp["error"]` to be `resp.get("error")` to avoid key error

## [0.9.21] - 2025-02-21
- Add title parameter and change labels in `MessageAssessment`

## [0.9.20] - 2025-02-01
- Add url parameter to `MessageAssessment.create_async` and `MessageAssessment.modify_async`

## [0.9.19] - 2025-01-31
- Add `MessageAssessment` resource

## [0.9.18] - 2025-01-22
- Removed `Invalid response body from API` from `retry_dict` as it's our own artificail error.

## [0.9.17] - 2025-01-03
- BREAKING CHANGE!! Removed unused `id` from `ShortTermMemory` create and find methods.

## [0.9.16] - 2024-12-19
- Corrected return type of `Search.create` and `Search.create_async` to `List[Search]`
- Retry on `Connection aborted` error

## [0.9.15] - 2024-12-06
- Add `Internal server error` and `You can retry your request` to the retry logic

## [0.9.14] - 2024-12-06
- Add `contentIds` to `Search.create` and `Search.create_async`

## [0.9.13] - 2024-11-21
- Add retry for `5xx` errors, add additional error message.

## [0.9.12] - 2024-11-21
- Include original error message in returned exceptions

## [0.9.11] - 2024-11-18
- Add  `ingestionConfig` to `UpsertParams.Input` parameters 

## [0.9.10] - 2024-10-23
- Remove `temperature` parameter from `Integrated.chat_stream_completion`, `Integrated.chat_stream_completion_async`, `ChatCompletion.create` and `ChatCompletion.create_async` methods. To use `temperature` parameter, set the attribute in `options` parameter instead.

## [0.9.9] - 2024-10-23
- Revert deletion of `Message.retrieve` method

## [0.9.8] - 2024-10-16
- Add `retries` for `_static_request` and `_static_request_async` in `APIResource` - When the error messages contains either  `"problem proxying the request"`,
        or `"Upstream service reached a hard timeout"`,
## [0.9.7] - 2024-09-23
- Add `completedAt` to `CreateParams` of `Message`

## [0.9.6] - 2024-09-03
- Added `metaDataFilter` to `Search` parameters.

## [0.9.5] - 2024-08-07
- Add `completedAt` to `ModifyParams`

## [0.9.4] - 2024-07-31
- Add `close` and `close_async` to `http_client`
- Make `httpx` the default client for async requests

## [0.9.3] - 2024-07-31
- `Search.create`, `Message`, `ChatCompletion` parameters that were marked `NotRequired` are now also `Optional`

## [0.9.2] - 2024-07-30
- Bug fix in `Search.create`: langugage -> language 

## [0.9.1] - 2024-07-30
- Added parameters to `Search.create` and `Search.create_async`
    - `language` for full text search
    - `reranker` to reranker search results

## [0.9.0] - 2024-07-29
- Added the possibility to make async requests to the unique APIs using either aiohttp or httpx as client
