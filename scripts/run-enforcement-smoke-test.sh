#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"

uv sync --extra dev
uv run pytest
uv run apseudo-format --check .
uv run apseudo-lint .
uv run apseudo-review . >/dev/null
uv run apseudo-lsp --version >/dev/null
uv run apseudo-mcp --version >/dev/null
uv run apseudo-explain APSEUDO-WHILE-001 >/dev/null
uv run apseudo-template bounded-review-loop >/dev/null
uv run apseudo-mermaid docs/examples/review-loop.apseudo --no-fence >/dev/null
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | scripts/apseudo-mcp >/tmp/apseudo-mcp-smoke.jsonl
uv run ruff check src tests integrations/agent-hooks
uv run pyright
python3 -m json.tool .claude/settings.json >/dev/null
python3 -m json.tool .codex/hooks.json >/dev/null
python3 -m json.tool .mcp.json >/dev/null
python3 - <<'PY'
import tomllib
from pathlib import Path
_ = tomllib.loads(Path('.codex/config.toml').read_text())
PY

if [ -d products/vscode-extension ] && command -v npm >/dev/null 2>&1; then
  (
    cd products/vscode-extension
    if [ ! -d node_modules ]; then
      if [ -f package-lock.json ]; then
        npm ci
      else
        npm install
      fi
    fi
    npm run check
  )
fi

echo "Enforcement smoke test passed."
