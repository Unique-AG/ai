#!/bin/bash

path_to_tangle_generated_files="./docs/.python_files"
path_to_examples="./docs/examples_from_docs/"

uv run entangled tangle --annotate naked --force

mkdir -p $path_to_examples
cp $path_to_tangle_generated_files/*.py $path_to_examples/


uv run entangled tangle --force 


uv run isort --float-to-top $path_to_examples 
uv run ruff format $path_to_examples 
uv run ruff check  $path_to_examples --fix --unsafe-fixes
uv run ruff check $path_to_examples --select F841 --fix --unsafe-fixes
uv run ruff format $path_to_examples 
