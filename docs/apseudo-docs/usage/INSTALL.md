---
schema_version: '1.1'
id: 'runbook-cxnpvn-installation-guide'
title: 'Installation Guide'
description: 'Installation guide for the Pythonic Agent Pseudocode toolkit and editor integrations.'
doc_type: 'runbook'
status: 'active'
created: '2026-07-08'
updated: '2026-07-09'
reviewed: null
owner: 'tooling-maintainers'
consumer: 'user'
tags:
  - 'runbook'
  - 'usage'
  - 'install'
aliases:
  - 'setup guide'
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Installation Guide

**Toolkit version:** 0.6.1

## Prerequisites

- Python 3.11+
- `uv`
- Git
- Node.js/npm for building the VS Code extension
- VS Code or compatible editor for the VS Code extension
- Kate/KDE with LSP Client plugin for Kate integration

## Install Python tooling

```bash
uv sync --extra dev
uv run pytest
uv run apseudo-format --check .
uv run apseudo-lint .
uv run apseudo-review .
```

## Install pre-commit and local enforcement

```bash
scripts/install-enforcement.sh
```

This installs pre-commit hooks and runs the enforcement smoke test.

## Build/install VS Code extension

```bash
cd products/vscode-extension
npm install
npm run check
npm run package
code --install-extension agent-pseudocode-0.6.1.vsix --force
```

The extension starts `apseudo-lsp`. If the server is not found, open the extension settings and point the server command at the repository `scripts/apseudo-lsp` path.

## Install Kate syntax highlighting

```bash
./scripts/install-kate-user.sh
```

Then enable Kate's LSP Client plugin and paste `products/kate-integration/lsp-client-settings.json` into the User Server Settings area. Use `products/kate-integration/lsp-client-settings.markdown-opt-in.json` only if you want Markdown LSP diagnostics in addition to syntax highlighting.

## Enable Claude Code hooks and skill

Files included:

```text
.claude/settings.json
.claude/skills/agent-pseudocode/SKILL.md
.mcp.json
```

Steps:

1. Open the repository in Claude Code.
2. Trust the project when prompted.
3. Confirm hooks are visible in the hooks UI.
4. Confirm the `agent-pseudocode` skill is visible in `/skills`.
5. Confirm the `agent-pseudocode` MCP server is connected.

## Enable Codex CLI hooks, skill, and MCP

Files included:

```text
.codex/hooks.json
.codex/config.toml
.agents/skills/agent-pseudocode/SKILL.md
```

Steps:

1. Open Codex from the repository or a subdirectory.
2. Trust project-local hooks if prompted.
3. Use `/hooks` to confirm hook definitions.
4. Use `/skills` or `$agent-pseudocode` to confirm skill discovery.
5. Use `/mcp` to confirm the `agent_pseudocode` MCP server.

## Required CI setup

The repository includes:

```text
.github/workflows/apseudo-lint.yml
```

Make the job named **Validate pseudocode standard** required in branch protection. Local hooks are useful, but CI is the merge gate.

## Full verification

Run this before tagging or distributing the toolkit:

```bash
uv sync --extra dev
uv run pytest
uv run apseudo-format --check .
uv run apseudo-lint .
uv run apseudo-review .
uv run ruff check src tests integrations/agent-hooks
uv run pyright
python3 -m json.tool .claude/settings.json
python3 -m json.tool .codex/hooks.json
python3 -m json.tool .mcp.json
cd products/vscode-extension && npm install && npm run check && npm run package
```

## Distribution notes

For one or two repositories, copy the whole toolkit or vendor it as a subdirectory. For many repositories, package the skills, hooks, MCP config, and scripts as a plugin or template repository so updates can be propagated consistently.
