# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
