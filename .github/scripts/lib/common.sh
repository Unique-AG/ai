#!/usr/bin/env bash
# Common library for GitHub scripts
# Provides shared utilities for color output, printing, and script metadata

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script metadata (set by calling script)
SCRIPT_NAME="${SCRIPT_NAME:-$(basename "$0")}"
VERSION="${VERSION:-1.0.0}"

# Function to print colored output
print_error() {
    echo -e "${RED}❌${NC} $1" >&2
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ️${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

# Show version
show_version() {
    echo "${SCRIPT_NAME} version ${VERSION}"
}

