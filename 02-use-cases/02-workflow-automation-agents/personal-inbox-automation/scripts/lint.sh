#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "=== py_compile ==="
find "$DIR/app" "$DIR/lambdas" "$DIR/scripts" -name "*.py" -exec python3 -m py_compile {} \;
echo "✓ All Python files compile"
