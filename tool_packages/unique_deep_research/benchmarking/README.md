# DeepResearch Benchmarking

This directory contains the benchmarking setup for evaluating the Unique Custom Deep Research Agent on the DeepResearch Bench benchmark. It's only intended for the RACE metrics


## Quick Start

```bash
# 1. clone the benchmarking repo
git clone https://github.com/Ayanami0730/deep_research_bench

# 2. Set environment
export UNIQUE_ENV_PATH="/path/to/your/.env"

# 3. Configure the run in run_unique_custom_bench.py

# 4. Parallel execution (faster, 3 concurrent tasks)
poetry run python benchmarking/run_unique_custom_bench.py --concurrency 3

# 5. After completion, setup evaluation in benchmarking/deep_research_bench/run_benchmark

# 7. set your env
GEMINI_API_KEY=sk_xxx
GOOGLE_GEMINI_BASE_URL=litellm....

# 8. run the benchmark
cd benchmarking/deep_research_bench && bash run_benchmark.sh
```
