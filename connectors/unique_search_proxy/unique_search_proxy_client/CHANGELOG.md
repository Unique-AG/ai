# Changelog

## [2026.32.0](https://github.com/Unique-AG/ai/compare/unique-search-proxy-v2026.30.0...unique-search-proxy-v2026.32.0) (2026-07-24)


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
