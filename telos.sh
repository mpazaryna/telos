#!/bin/bash
# Launch telos interactive TUI
cd "$(dirname "$0")" && uv run telos "$@"
