#!/bin/bash
set -euo pipefail

path_to_tangle_generated_files="./docs/.python_files"
path_to_examples="./docs/examples_from_docs/"

make_vscode_notebook_like() {
    local examples_dir="$1"
    echo "Making Python files VSCode notebook-like..."

    for file in "$examples_dir"/*.py; do
        if [ ! -f "$file" ]; then
            continue
        fi

        if grep -q '^# %%' "$file"; then
            continue
        fi

        if grep -q '^# /// script' "$file"; then
            awk '
                /^# \/\/\/ script/ { in_script = 1 }
                {
                    print
                    if (in_script && /^# \/\/\/$/) {
                        print ""
                        print "# %%"
                        in_script = 0
                    }
                }
            ' "$file" > "$file.tmp"
            mv "$file.tmp" "$file"
        else
            { echo "# %%"; cat "$file"; } > "$file.tmp"
            mv "$file.tmp" "$file"
        fi
        echo "  ✓ Added cell marker to $(basename "$file")"
    done
}

uv run entangled tangle --annotate naked --force

mkdir -p $path_to_examples
cp $path_to_tangle_generated_files/*.py $path_to_examples/


uv run entangled tangle --force 


uv run isort --float-to-top $path_to_examples 
uv run ruff format $path_to_examples 
uv run ruff check  $path_to_examples --fix --unsafe-fixes
uv run ruff check $path_to_examples --select F841 --fix --unsafe-fixes
uv run ruff format $path_to_examples 

make_vscode_notebook_like $path_to_examples
