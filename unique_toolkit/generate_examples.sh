#!/bin/bash

path_to_tangle_generated_files="./docs/.python_files"
path_to_examples="./docs/examples_from_docs/"

make_vscode_notebook_like() {
    local examples_dir="$1"
    echo "Making Python files VSCode notebook-like..."
    
    for file in "$examples_dir"/*.py; do
        if [ -f "$file" ]; then
            # Create temp file with # %% at the top, then append original content
            echo "# %%" > "$file.tmp"
            cat "$file" >> "$file.tmp"
            mv "$file.tmp" "$file"
            echo "  ✓ Added cell marker to $(basename "$file")"
        fi
    done
}

poetry run entangled tangle --annotate naked --force

mkdir -p $path_to_examples
cp $path_to_tangle_generated_files/*.py $path_to_examples/


poetry run entangled tangle --force 


poetry run isort --float-to-top $path_to_examples 
poetry run ruff format $path_to_examples 
poetry run ruff check  $path_to_examples --fix --unsafe-fixes
poetry run ruff check $path_to_examples --select F841 --fix --unsafe-fixes
poetry run ruff format $path_to_examples 

make_vscode_notebook_like $path_to_examples