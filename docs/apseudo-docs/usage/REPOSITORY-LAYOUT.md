---
schema_version: '1.1'
id: 'runbook-uzku0w-repository-layout'
title: 'Repository Layout'
description: 'Guide to the repository layout for Pythonic Agent Pseudocode tooling and documentation.'
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
aliases: []
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Repository Layout

This repository is arranged for standalone GitHub development while keeping the later `project-standards` conversion path clean.

## Root policy

The root keeps only files that are either conventional repository entry points or required for tool discovery:

| Root item | Reason it remains at root |
| --- | --- |
| `README.md`, `CHANGELOG.md`, `LICENSE` | Standard project entry points. |
| `pyproject.toml`, `uv.lock` | Python package and uv environment source of truth. |
| `AGENTS.md`, `CLAUDE.md` | Agent instruction discovery. |
| `.agents/`, `.claude/`, `.codex/` | Agent skill, hook, and config discovery locations. |
| `.github/` | GitHub Actions discovery. |
| `.apseudo/`, `.apseudo-lint.toml`, `.mcp.json` | Runner registry, validator config, and MCP discovery. |
| `.pre-commit-config.yaml`, `.pre-commit-hooks.yaml` | pre-commit discovery and local hook publishing. |
| `.editorconfig`, `.gitignore` | Editor and Git conventions. |
| `src/`, `tests/`, `scripts/` | Python package, test suite, and source-tree command wrappers. |
| `docs/`, `products/`, `integrations/` | Grouped documentation, editor products, and agent integration implementation. |

## Grouped areas

| Folder | Contents |
| --- | --- |
| `docs/` | All human-facing reference, usage, specification, review, roadmap, source, and example documents. |
| `products/` | Editor/distribution products such as the VS Code extension and Kate integration. |
| `integrations/agent-hooks/` | Shared Claude Code and Codex hook implementation. The root `.claude` and `.codex` configs point here. |
| `src/apseudo_lint/` | Shared Python implementation used by CLI tools, LSP, MCP, runner, hooks, and tests. |
| `scripts/` | Source-tree wrappers for console commands and install/smoke-test helpers. |
| `tests/` | Unit tests and valid/invalid fixtures. |

## Path convention

Repository documentation should use paths relative to the repository root. That keeps instructions stable when a document moves within `docs/` and matches the way agents normally operate from the project root.
