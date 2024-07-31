# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.3] - 2024-07-31
`Search.create`, `Message`, `ChatCompletion` parameters that were marked `NotRequired` are now also `Optional`

## [0.9.2] - 2024-07-30
Bug fix in `Search.create`: langugage -> language 

## [0.9.1] - 2024-07-30
- Added parameters to `Search.create`
    - `language` for full text search
    - `reranker` to reranker search results
