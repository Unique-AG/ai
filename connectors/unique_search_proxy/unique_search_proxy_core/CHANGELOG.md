# Changelog

## [2026.32.0](https://github.com/Unique-AG/ai/compare/unique-search-proxy-core-v2026.30.0...unique-search-proxy-core-v2026.32.0) (2026-07-24)


### Features

* **bing:** migrate grounding to Agents v2 + Responses API [UN-23345] ([#2141](https://github.com/Unique-AG/ai/issues/2141)) ([46c2b76](https://github.com/Unique-AG/ai/commit/46c2b76548b19ffeeb40d52b31cfcee970f61f65))
* **search-proxy:** per-URL crawl outcome metrics with HTTP status ([#2132](https://github.com/Unique-AG/ai/issues/2132)) ([0665906](https://github.com/Unique-AG/ai/commit/066590624739ffa19e26579c6e542634073166d5))


### Bug Fixes

* Url Safety blocks individual urls instead of batch ([#2137](https://github.com/Unique-AG/ai/issues/2137)) ([3855ab0](https://github.com/Unique-AG/ai/commit/3855ab02dfd8d7c193339614cff854ebe8611042))


### Miscellaneous

* arm release 2026.32.0 ([6084f04](https://github.com/Unique-AG/ai/commit/6084f0413c8611f1493a00288e4b69797198c3cd))

## [2026.30.0](https://github.com/Unique-AG/ai/compare/unique-search-proxy-core-v2026.28.0...unique-search-proxy-core-v2026.30.0) (2026-07-17)


### Features

* **search-proxy:** enforce tenant context headers and enrich request logs ([#2090](https://github.com/Unique-AG/ai/issues/2090)) ([23b2562](https://github.com/Unique-AG/ai/commit/23b25623ce34859a1b8422da3b7764f245797fd4))
* **search-proxy:** tighten search engine config schemas [UN-21235] ([#2040](https://github.com/Unique-AG/ai/issues/2040)) ([0b817c0](https://github.com/Unique-AG/ai/commit/0b817c08267b6730eb21a231557ac4eeb3b81b83))


### Bug Fixes

* Pass user agent to head request for url safety redirect resolution ([#2067](https://github.com/Unique-AG/ai/issues/2067)) ([b526d5d](https://github.com/Unique-AG/ai/commit/b526d5d348272298717ef160e91080280419cc49))


### Miscellaneous

* arm release 2026.30.0 ([94e018f](https://github.com/Unique-AG/ai/commit/94e018fa010fb5a0ffd8f449cf078c604b7c12ee))

## [2026.28.0](https://github.com/Unique-AG/ai/compare/unique-search-proxy-core-v2026.26.0...unique-search-proxy-core-v2026.28.0) (2026-07-03)


### Features

* Migrate search engine configuration from proxy core ([#1966](https://github.com/Unique-AG/ai/issues/1966)) ([6693d37](https://github.com/Unique-AG/ai/commit/6693d378b1d5626ec881b2f91ed490afb7cf4471))


### Miscellaneous

* arm release 2026.28.0 ([e890f5e](https://github.com/Unique-AG/ai/commit/e890f5ecc6217d885dbdb4a3d6f093237320e1bd))

## [2026.26.0](https://github.com/Unique-AG/ai/compare/unique-search-proxy-core-v2026.24.0...unique-search-proxy-core-v2026.26.0) (2026-06-22)


### Features

* Add Url Safety service to search proxy ([#1880](https://github.com/Unique-AG/ai/issues/1880)) ([c592a18](https://github.com/Unique-AG/ai/commit/c592a18cc948df12fcd3beef7630f988d2d3fe2f))
* Display Settings at pod startup ([#1890](https://github.com/Unique-AG/ai/issues/1890)) ([d7a4d1c](https://github.com/Unique-AG/ai/commit/d7a4d1c11450cef2a18ea20d106711abfea0dc99))
* Migrate all search engines and all crawlers to search proxy ([#1876](https://github.com/Unique-AG/ai/issues/1876)) ([0602244](https://github.com/Unique-AG/ai/commit/06022440fb64b50a42bbfb4d9440a3406884237c))
* Migrating Web Interaction responsibilities to web search proxy ([#1793](https://github.com/Unique-AG/ai/issues/1793)) ([8288f79](https://github.com/Unique-AG/ai/commit/8288f794fb9dad1985af7023e8e25183a13cde9a))


### Miscellaneous

* arm release 2026.18.0 ([#1493](https://github.com/Unique-AG/ai/issues/1493)) ([bc435b2](https://github.com/Unique-AG/ai/commit/bc435b2c5838a9e16484fb054beb277b8262c136))
* arm release 2026.20.0 ([#1506](https://github.com/Unique-AG/ai/issues/1506)) ([0820dc9](https://github.com/Unique-AG/ai/commit/0820dc9a1c661470c2ef44ed2eed6830b508ca8d))
* arm release 2026.22.0 ([3fe07bd](https://github.com/Unique-AG/ai/commit/3fe07bdafc85a45f8275a18b72f6ebe766c15464))
* arm release 2026.24.0 ([2b3ff5d](https://github.com/Unique-AG/ai/commit/2b3ff5d2e13c4c98cd0012f0306db10f980aa886))
* arm release 2026.26.0 ([d3c79b3](https://github.com/Unique-AG/ai/commit/d3c79b385f2714ab9c6237a545da21dea0cfb34a))
