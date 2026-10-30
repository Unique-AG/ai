# Changelog

## [2026.46.0](https://github.com/Unique-AG/ai/compare/unique-search-proxy-v2026.44.0...unique-search-proxy-v2026.46.0) (2026-10-30)


### Bug Fixes

* **search-proxy:** bump base chart to pick up CiliumNetworkPolicy sync-wave default ([#2649](https://github.com/Unique-AG/ai/issues/2649)) ([3f1d88b](https://github.com/Unique-AG/ai/commit/3f1d88be07ac089de6314558d7f3e1d3148bf3ba))
* **search-proxy:** default to 2 workers with 4 crawls each ([#2627](https://github.com/Unique-AG/ai/issues/2627)) ([1bbe5f2](https://github.com/Unique-AG/ai/commit/1bbe5f2d4202a79324366426f36ac3e9645c30c4))
* **searchproxy:** trivy cves ([#2635](https://github.com/Unique-AG/ai/issues/2635)) ([afa596c](https://github.com/Unique-AG/ai/commit/afa596c9b4b0231895ff70f44029a9a525f746e9))


### Miscellaneous

* arm release 2026.46.0 ([0a6e2c9](https://github.com/Unique-AG/ai/commit/0a6e2c9b101fd5fa00919a5b2eb5b81994215fed))

## [2026.44.0](https://github.com/Unique-AG/ai/compare/unique-search-proxy-v2026.42.0...unique-search-proxy-v2026.44.0) (2026-10-23)


### Features

* **search-proxy:** add Customized API provider [UN-26736] ([#2537](https://github.com/Unique-AG/ai/issues/2537)) ([12428e5](https://github.com/Unique-AG/ai/commit/12428e5d3e2568b3d3058ccb964fd85dcaea81a2))
* **search-proxy:** attribute web search requests to company, user and entry point [UN-24394] ([#2520](https://github.com/Unique-AG/ai/issues/2520)) ([5714fbd](https://github.com/Unique-AG/ai/commit/5714fbdac325d42af0b87eaf4843568c3ba8655e))
* **search-proxy:** make chart safe by default [UN-24394] ([#2527](https://github.com/Unique-AG/ai/issues/2527)) ([48f4645](https://github.com/Unique-AG/ai/commit/48f4645c1d0ae82bc0c91cd1757596032e479da5))


### Bug Fixes

* **search-proxy:** bound total bytes per crawl request ([#2584](https://github.com/Unique-AG/ai/issues/2584)) ([91630e4](https://github.com/Unique-AG/ai/commit/91630e4579a87c2845b69abb8505bb9171bc8a73))
* **search-proxy:** cap crawl timeouts and concurrency ([#2586](https://github.com/Unique-AG/ai/issues/2586)) ([cd34c7d](https://github.com/Unique-AG/ai/commit/cd34c7dffac78ced7b11045beda019a580b76060))
* **search-proxy:** cap decoded crawl bodies ([#2583](https://github.com/Unique-AG/ai/issues/2583)) ([7d86f34](https://github.com/Unique-AG/ai/commit/7d86f34085d37e19ef8bb66d8e6094d1fec0d6b4))
* **search-proxy:** cap outbound response size ([#2582](https://github.com/Unique-AG/ai/issues/2582)) ([2997f00](https://github.com/Unique-AG/ai/commit/2997f0028fb5265f45645b719e9c193fc3cf8f89))
* **search-proxy:** limit URL count and length per crawl ([#2585](https://github.com/Unique-AG/ai/issues/2585)) ([e6f145c](https://github.com/Unique-AG/ai/commit/e6f145ce918d6c428eb60d432c222fefae5dd49f))
* **search-proxy:** patch Trivy image vulnerabilities ([#2595](https://github.com/Unique-AG/ai/issues/2595)) ([4a6ecb7](https://github.com/Unique-AG/ai/commit/4a6ecb7f85449672ea1667a8c1aa8f6e8881d6b2))
* **search-proxy:** resolve Vertex redirects safely [UN-26738] ([#2599](https://github.com/Unique-AG/ai/issues/2599)) ([540cd90](https://github.com/Unique-AG/ai/commit/540cd9089e4bdcb82c96189c9dadfba64890e388))
* **search-proxy:** route agent search through egress proxy ([#2559](https://github.com/Unique-AG/ai/issues/2559)) ([52eee59](https://github.com/Unique-AG/ai/commit/52eee59cfafc6c7bf5e9b7ec2e2a5216a783f5ee))
* **web-search:** stop logging crawled URLs and search queries [UN-27835] ([#2600](https://github.com/Unique-AG/ai/issues/2600)) ([454dff2](https://github.com/Unique-AG/ai/commit/454dff2247a074ae7dd5d80f6c81e3c4476fa9ee))
* **web-search:** use Foundry citation URLs for Bing results [UN-26467] ([#2614](https://github.com/Unique-AG/ai/issues/2614)) ([c3fabcf](https://github.com/Unique-AG/ai/commit/c3fabcfa333714e79cea3160ed201789950fb171))


### Miscellaneous

* arm release 2026.44.0 ([4580110](https://github.com/Unique-AG/ai/commit/45801105f80b0faa89d69d19917913c7c6b093aa))

## [2026.42.0](https://github.com/Unique-AG/ai/compare/unique-search-proxy-v2026.40.0...unique-search-proxy-v2026.42.0) (2026-10-09)


### Features

* **toolkit:** add GPT-6.1 Sol model info ([#2496](https://github.com/Unique-AG/ai/issues/2496)) ([e18ad7d](https://github.com/Unique-AG/ai/commit/e18ad7d24f556193edfa4055b0d8586a1551bd09))


### Bug Fixes

* **search-proxy:** validate disabled URL safety proxy config ([#2518](https://github.com/Unique-AG/ai/issues/2518)) ([b6ecd31](https://github.com/Unique-AG/ai/commit/b6ecd31475f591c6c051edef9623015935469644))
* **search-proxy:** validate redirects during basic crawl ([#2521](https://github.com/Unique-AG/ai/issues/2521)) ([7098320](https://github.com/Unique-AG/ai/commit/70983209f43191e2a634aa08d2e39a921ef4653f))


### Miscellaneous

* arm release 2026.42.0 ([da4063c](https://github.com/Unique-AG/ai/commit/da4063cd617b6c3cd03019735a1fc8d34a574538))

## [2026.40.0](https://github.com/Unique-AG/ai/compare/unique-search-proxy-v2026.38.0...unique-search-proxy-v2026.40.0) (2026-09-24)


### Miscellaneous

* arm release 2026.40.0 ([f4a6377](https://github.com/Unique-AG/ai/commit/f4a6377a9e39f6bf9da0289d790f8f80e1bb89ed))

## [2026.38.0](https://github.com/Unique-AG/ai/compare/unique-search-proxy-v2026.36.0...unique-search-proxy-v2026.38.0) (2026-09-10)


### Features

* **search-proxy:** resolve proxy credentials from settings or the request [UN-25449] ([#2435](https://github.com/Unique-AG/ai/issues/2435)) ([dbea4df](https://github.com/Unique-AG/ai/commit/dbea4df77c8305102fe5ec53222620076a555044))


### Bug Fixes

* **search-proxy:** rework Bing grounding params as fixed admin values [UN-24652] ([#2397](https://github.com/Unique-AG/ai/issues/2397)) ([38edc46](https://github.com/Unique-AG/ai/commit/38edc465bc526ee7ab5568abce97985a87795ea8))


### Miscellaneous

* arm release 2026.38.0 ([c827b03](https://github.com/Unique-AG/ai/commit/c827b03349c0f510c235b55762386a36f93910b1))

## [2026.36.0](https://github.com/Unique-AG/ai/compare/unique-search-proxy-v2026.34.0...unique-search-proxy-v2026.36.0) (2026-08-31)


### Features

* **search-proxy:** add count tables and scope HTTP panels to proxy ([#2277](https://github.com/Unique-AG/ai/issues/2277)) ([9eb4776](https://github.com/Unique-AG/ai/commit/9eb4776e74499dd6213ed329382fd6745f99049a))
* **search-proxy:** add Key Vault secrets Terraform module ([#2326](https://github.com/Unique-AG/ai/issues/2326)) ([9adc9de](https://github.com/Unique-AG/ai/commit/9adc9dea2392f7072ba7774881bb7691e52efd82))
* **search-proxy:** forward Bing grounding knobs to Foundry ([#2331](https://github.com/Unique-AG/ai/issues/2331)) ([cf4caaa](https://github.com/Unique-AG/ai/commit/cf4caaa1cb931be1300db9fd75f931f8a4ff54ef))


### Miscellaneous

* arm release 2026.36.0 ([7882253](https://github.com/Unique-AG/ai/commit/788225328a78ebc31e264e085d3d843e145063fb))

## [2026.34.0](https://github.com/Unique-AG/ai/compare/unique-search-proxy-v2026.32.0...unique-search-proxy-v2026.34.0) (2026-08-14)


### ⚠ BREAKING CHANGES

* **web-search:** Deployments that pinned `BING_AGENT_AGENT_ID`, request `agentId`, BingSearchConfig `agent_id`/`endpoint`, or `AZURE_AI_ASSISTANT_ID` will silently switch to hash-based auto-provisioning. Project endpoint for the legacy Azure path must come from env (`azure_ai_project_endpoint` / `BING_AGENT_ENDPOINT` on the proxy).

### Bug Fixes

* **search-proxy:** pin uv in the container image ([#2186](https://github.com/Unique-AG/ai/issues/2186)) ([7d70692](https://github.com/Unique-AG/ai/commit/7d7069239655d364ff81b49ace574d655b7e9e6d))


### Miscellaneous

* arm release 2026.34.0 ([994fbe8](https://github.com/Unique-AG/ai/commit/994fbe88cd4873caa0c8319489e72bb25ac159dc))
* **web-search:** decommission Bing agent_id for auto-provisioning ([#2263](https://github.com/Unique-AG/ai/issues/2263)) ([1166358](https://github.com/Unique-AG/ai/commit/1166358f5064bb63f86a96c9e408abb404ec6f35))

## [2026.32.0](https://github.com/Unique-AG/ai/compare/unique-search-proxy-v2026.30.0...unique-search-proxy-v2026.32.0) (2026-07-31)


### Features

* **bing:** migrate grounding to Agents v2 + Responses API [UN-23345] ([#2141](https://github.com/Unique-AG/ai/issues/2141)) ([46c2b76](https://github.com/Unique-AG/ai/commit/46c2b76548b19ffeeb40d52b31cfcee970f61f65))
* **search-proxy:** per-URL crawl outcome metrics with HTTP status ([#2132](https://github.com/Unique-AG/ai/issues/2132)) ([0665906](https://github.com/Unique-AG/ai/commit/066590624739ffa19e26579c6e542634073166d5))
* **search-proxy:** provision Grafana dashboard via chart ([#2129](https://github.com/Unique-AG/ai/issues/2129)) ([57806ed](https://github.com/Unique-AG/ai/commit/57806ed83f911eb514f27be6022629024006a547))


### Bug Fixes

* **security:** bump mcp and starlette via constraint-dependencies ([#2126](https://github.com/Unique-AG/ai/issues/2126)) ([aef8e10](https://github.com/Unique-AG/ai/commit/aef8e107a221d3df1579cad1fb9a78655ce16590))


### Miscellaneous

* arm release 2026.32.0 ([6084f04](https://github.com/Unique-AG/ai/commit/6084f0413c8611f1493a00288e4b69797198c3cd))

## [2026.30.0](https://github.com/Unique-AG/ai/compare/unique-search-proxy-v2026.28.0...unique-search-proxy-v2026.30.0) (2026-07-17)


### Features

* **search-proxy:** enforce tenant context headers and enrich request logs ([#2090](https://github.com/Unique-AG/ai/issues/2090)) ([23b2562](https://github.com/Unique-AG/ai/commit/23b25623ce34859a1b8422da3b7764f245797fd4))
* **search-proxy:** tighten search engine config schemas [UN-21235] ([#2040](https://github.com/Unique-AG/ai/issues/2040)) ([0b817c0](https://github.com/Unique-AG/ai/commit/0b817c08267b6730eb21a231557ac4eeb3b81b83))


### Miscellaneous

* arm release 2026.30.0 ([94e018f](https://github.com/Unique-AG/ai/commit/94e018fa010fb5a0ffd8f449cf078c604b7c12ee))

## [2026.28.0](https://github.com/Unique-AG/ai/compare/unique-search-proxy-v2026.26.0...unique-search-proxy-v2026.28.0) (2026-07-03)


### Features

* Autogenerate helm-chart from secret settings ([#1913](https://github.com/Unique-AG/ai/issues/1913)) ([13fe002](https://github.com/Unique-AG/ai/commit/13fe0024ee038d10a50b4bad5e65ead6faaa9a6b))
* Migrate search engine configuration from proxy core ([#1966](https://github.com/Unique-AG/ai/issues/1966)) ([6693d37](https://github.com/Unique-AG/ai/commit/6693d378b1d5626ec881b2f91ed490afb7cf4471))


### Bug Fixes

* **search-proxy:** preserve newlines between Cilium egress rules ([#1935](https://github.com/Unique-AG/ai/issues/1935)) ([d9e6527](https://github.com/Unique-AG/ai/commit/d9e652726e4908476ab5c96322079ad499558616))
* **search-proxy:** use LogSecretStr for Bing agent secret fields ([#1933](https://github.com/Unique-AG/ai/issues/1933)) ([0499a68](https://github.com/Unique-AG/ai/commit/0499a68dea8ab785e2ec54c90600088d8ce3c055))
* **unique_search_proxy:** exact host match in test URL gate (CodeQL py/incomplete-url-substring-sanitization) ([#1962](https://github.com/Unique-AG/ai/issues/1962)) ([c789571](https://github.com/Unique-AG/ai/commit/c78957170e888a531fb1585fbb5a4262c1e37822))


### Miscellaneous

* arm release 2026.28.0 ([e890f5e](https://github.com/Unique-AG/ai/commit/e890f5ecc6217d885dbdb4a3d6f093237320e1bd))

## [2026.26.0](https://github.com/Unique-AG/ai/compare/unique-search-proxy-v2026.24.0...unique-search-proxy-v2026.26.0) (2026-06-22)


### Features

* Add Url Safety service to search proxy ([#1880](https://github.com/Unique-AG/ai/issues/1880)) ([c592a18](https://github.com/Unique-AG/ai/commit/c592a18cc948df12fcd3beef7630f988d2d3fe2f))
* Display Settings at pod startup ([#1890](https://github.com/Unique-AG/ai/issues/1890)) ([d7a4d1c](https://github.com/Unique-AG/ai/commit/d7a4d1c11450cef2a18ea20d106711abfea0dc99))
* Migrate all search engines and all crawlers to search proxy ([#1876](https://github.com/Unique-AG/ai/issues/1876)) ([0602244](https://github.com/Unique-AG/ai/commit/06022440fb64b50a42bbfb4d9440a3406884237c))
* Migrating Web Interaction responsibilities to web search proxy ([#1793](https://github.com/Unique-AG/ai/issues/1793)) ([8288f79](https://github.com/Unique-AG/ai/commit/8288f794fb9dad1985af7023e8e25183a13cde9a))
* **search-proxy:** migrate helm chart to latest base + googleSearch domain config ([#1893](https://github.com/Unique-AG/ai/issues/1893)) ([d47b737](https://github.com/Unique-AG/ai/commit/d47b7377d38eee1012ef6c584c688d4a785167a4))


### Bug Fixes

* Remove experimental from entrypoint ([#1810](https://github.com/Unique-AG/ai/issues/1810)) ([7045696](https://github.com/Unique-AG/ai/commit/7045696677adf1e0f256a4424890dd10f1a23730))
* **search-proxy:** trigger search-proxy redeployment ([#1815](https://github.com/Unique-AG/ai/issues/1815)) ([05131f0](https://github.com/Unique-AG/ai/commit/05131f0c5ed33642fc2342f1b43dd0ff31c4ab74))
* **search-proxy:** use uv sync --frozen with root build context for search-proxy container ([#1812](https://github.com/Unique-AG/ai/issues/1812)) ([66eafe7](https://github.com/Unique-AG/ai/commit/66eafe7b4fdb1dd432ee2a137507ce3ff3cfd7b7))


### Miscellaneous

* arm release 2026.18.0 ([#1493](https://github.com/Unique-AG/ai/issues/1493)) ([bc435b2](https://github.com/Unique-AG/ai/commit/bc435b2c5838a9e16484fb054beb277b8262c136))
* arm release 2026.20.0 ([#1506](https://github.com/Unique-AG/ai/issues/1506)) ([0820dc9](https://github.com/Unique-AG/ai/commit/0820dc9a1c661470c2ef44ed2eed6830b508ca8d))
* arm release 2026.22.0 ([3fe07bd](https://github.com/Unique-AG/ai/commit/3fe07bdafc85a45f8275a18b72f6ebe766c15464))
* arm release 2026.24.0 ([2b3ff5d](https://github.com/Unique-AG/ai/commit/2b3ff5d2e13c4c98cd0012f0306db10f980aa886))
* arm release 2026.26.0 ([d3c79b3](https://github.com/Unique-AG/ai/commit/d3c79b385f2714ab9c6237a545da21dea0cfb34a))
