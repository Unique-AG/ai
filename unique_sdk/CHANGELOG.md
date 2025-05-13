# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## [0.9.13] - 2024-10-23
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
