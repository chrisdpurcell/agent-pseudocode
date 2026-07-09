#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"

uv sync --extra dev
uv run pytest
uv run apseudo-format --check .
uv run apseudo-lint .
uv run apseudo-review . >/dev/null
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
uv run pre-commit run --all-files

cat <<'MSG'

Agent Pseudocode enforcement installed.

Next checks:
  - Commit .github/workflows/apseudo-lint.yml so GitHub Actions can run.
  - In Claude Code, inspect project hooks with /hooks and skills with /skills.
  - In Claude Code, confirm the agent-pseudocode MCP server from .mcp.json.
  - In Codex, inspect and trust project hooks with /hooks.
  - In Codex, inspect the agent-pseudocode skill with /skills and MCP with /mcp.
  - Make the GitHub Actions job required in branch protection if this is a protected repo.
MSG
