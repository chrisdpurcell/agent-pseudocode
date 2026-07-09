---
schema_version: '1.1'
id: 'runbook-6j08dn-agent-pseudocode-syntax-toolkit'
title: 'agent-pseudocode-syntax-toolkit'
description: 'Usage guide for the Pythonic Agent Pseudocode command-line toolkit.'
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
  - 'cli'
aliases:
  - 'apseudo'
  - 'apseudo-lint'
  - 'apseudo-format'
  - 'apseudo-template'
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# agent-pseudocode-syntax-toolkit

> **CLI documentation profile:** Packaged (per the `cli-documentation` standard). The unified `apseudo` dispatcher exposes 9 subcommands, which exceeds the "~5-7 top-level subcommands" Packaged-deep signal on count alone, but the standard is explicit that nesting/count alone never forces the deep tier — this repo stays Packaged as a deliberate tailoring.

## NAME

`apseudo` — lint, format, review, serve, document, and execute Pythonic Agent Pseudocode.

## SYNOPSIS

```text
apseudo <command> [<args>...]
apseudo lint [<path>...]
apseudo format [--check] [<path>...]
apseudo review [<path>]
apseudo mermaid <script.apseudo>
apseudo run [AGENT] [MODE] [OPTIONS] <script-or-name> [-- <key=value>...]
apseudo replay <run-dir>
apseudo doctor [--claude | --codex] [--json]
apseudo provider-test [--json]
apseudo docs generate [--output <path>]
apseudo {--help | --version}

apseudo-run [AGENT] [MODE] [OPTIONS] <script.apseudo> [-- <key=value>...]
apseudo-claude [MODE] [OPTIONS] <script.apseudo> [-- <key=value>...]
apseudo-codex [MODE] [OPTIONS] <script.apseudo> [-- <key=value>...]
```

## DESCRIPTION

`agent-pseudocode-syntax-toolkit` provides a complete local toolchain for the Pythonic Agent Pseudocode convention:

- syntax highlighting assets for VS Code and Kate;
- formatter and linter;
- language server with diagnostics, completion, hover, symbols, folding, and code actions;
- MCP server for agent-facing validation and template tools;
- Claude Code and Codex CLI hook scripts;
- executable `.apseudo` runner that launches Claude or Codex headlessly;
- registry and documentation generation for executable agent tasks.

The unified `apseudo` command is the human-facing entry point. Standalone commands remain public and scriptable for CI and editor integrations.

## OPTIONS

### `apseudo lint`

Validate pseudocode files and Markdown fenced blocks.

```text
apseudo lint [<path>...] [--changed] [--strict]
```

Exit status: `0` valid, non-zero findings or operator errors.

### `apseudo format`

Format pseudocode files and Markdown fenced blocks.

```text
apseudo format [<path>...] [--check] [--changed]
```

Use `--check` in CI and hooks. Omit `--check` to write changes.

### `apseudo review`

Run project-level completeness checks across the standard, tooling, docs, and examples.

```text
apseudo review [<path>]
```

### `apseudo mermaid`

Render a Mermaid view from a pseudocode process.

```text
apseudo mermaid <script.apseudo>
```

### `apseudo run`

Resolve an executable script by path or `.apseudo/scripts.toml` registry name, then delegate to `apseudo-run`.

```text
apseudo run [AGENT] [MODE] [OPTIONS] <script-or-name> [-- <key=value>...]
```

See [`RUNNER-USAGE.md`](RUNNER-USAGE.md) for the full option contract.

### `apseudo replay`

Summarize a saved run directory.

```text
apseudo replay .apseudo/runs/<run-id>
```

### `apseudo doctor`

Check local provider availability and project integration files.

```text
apseudo doctor [--claude | --codex] [--json]
```

The command checks whether `claude` and/or `codex` are on `$PATH`, attempts `--version`, and reports whether `.claude/settings.json`, `.codex/hooks.json`, `.mcp.json`, and `.apseudo/scripts.toml` are present.

### `apseudo provider-test`

Run a fake-provider smoke test of the executable runner path.

```text
apseudo provider-test [--json]
```

This test does not call real Claude or Codex. It verifies local runner plumbing.

### `apseudo docs generate`

Generate Markdown documentation for registered executable scripts.

```text
apseudo docs generate [--output <path>]
```

Default output: `docs/apseudo-docs/usage/agent-tasks.md`.

## apseudo-lint (standalone entry point)

`apseudo-lint` is a standalone console-script alias for `apseudo lint` — see the `apseudo lint` entry above for the full `NAME`/`SYNOPSIS`/`OPTIONS`/`EXIT STATUS` contract, which applies identically to the standalone invocation.

## apseudo-format (standalone entry point)

`apseudo-format` is a standalone console-script alias for `apseudo format` — see the `apseudo format` entry above for the full `NAME`/`SYNOPSIS`/`OPTIONS`/ `EXIT STATUS` contract, which applies identically to the standalone invocation.

## apseudo-lsp

`apseudo-lsp` has no `apseudo <subcommand>` equivalent — it is a standalone `[project.scripts]` entry point only, documented here in full.

### NAME

`apseudo-lsp` — Agent Pseudocode language server.

### SYNOPSIS

```text
apseudo-lsp [--stdio] [--trace]
apseudo-lsp {--help | --version}
```

### DESCRIPTION

`apseudo-lsp` implements a minimal Language Server Protocol server over stdio for Agent Pseudocode and Markdown `apseudo` fenced blocks. It delegates all semantic checks to the same formatter/linter used by the CLI, hooks, CI, and MCP server, and provides diagnostics, completion, hover, document formatting, code actions, document symbols, folding ranges, definitions, references, and workspace symbols. It is launched by editor LSP clients (VS Code, Kate) rather than invoked directly by users.

### OPTIONS

#### `--stdio`

Run the server over stdio. This is the default transport and exists for editor-client compatibility; the flag is accepted but has no effect beyond documenting client intent.

#### `--trace`

Log LSP message flow (method names for incoming/outgoing messages) to stderr.

#### `--version`

Print the `apseudo-lsp` version and exit.

### EXIT STATUS

| Code | Meaning                                                         |
| ---: | --------------------------------------------------------------- |
|  `0` | Clean shutdown — the client sent `shutdown` followed by `exit`. |
|  `1` | The client sent `exit` without a prior `shutdown` request.      |
|  `2` | Invalid CLI usage (`argparse` error).                           |

## apseudo-explain

`apseudo-explain` has no `apseudo <subcommand>` equivalent — it is a standalone `[project.scripts]` entry point only, documented here in full.

### NAME

`apseudo-explain` — explain `APSEUDO-*` linter rules and approved convention guidance.

### SYNOPSIS

```text
apseudo-explain [<code>...] [--json]
apseudo-explain {--help | --version}
```

### DESCRIPTION

`apseudo-explain` prints human-readable (or, with `--json`, machine-readable) guidance for one or more `APSEUDO-*` rule codes emitted by `apseudo lint`. Omitting all rule codes lists every known rule with its code, severity, and title.

### OPTIONS

#### `<code>...`

Zero or more rule codes to explain (for example `APSEUDO-BRANCH-001`). Case insensitive. Omit to list all rules.

#### `--json`

Emit JSON instead of Markdown/text.

#### `--version`

Print the `apseudo-explain` version and exit.

### EXIT STATUS

| Code | Meaning |
| --: | --- |
| `0` | Success — rules listed or explained. |
| `2` | One or more requested rule codes are unknown, or invalid CLI usage (`argparse` error). |

## EXIT STATUS

| Code | Meaning |
| --: | --- |
| `0` | Success. |
| `1` | Findings, failed provider availability check, or semantic runner outcome such as findings. |
| `2` | Invalid CLI usage for commands using `argparse`. |
| `10` | Runner outcome `NeedsUserDecision`. |
| `20` | Runner outcome `Blocked`. |
| `30` | Runner pseudocode validation failed. |
| `31` | Runner configuration or metadata error. |
| `40` | Provider command failed. |
| `41` | Provider output did not match the outcome schema. |
| `50` | Runner safety policy blocked execution. |

## ENVIRONMENT

| Variable          | Meaning                                                      |
| ----------------- | ------------------------------------------------------------ |
| `APSEUDO_AGENT`   | Default executable runner agent: `claude` or `codex`.        |
| `APSEUDO_RUN_ID`  | Set inside provider subprocesses when `--run-dir` is active. |
| `APSEUDO_RUN_DIR` | Set inside provider subprocesses when `--run-dir` is active. |
| `PYTHONPATH`      | Used by source-tree wrapper scripts under `scripts/`.        |

## FILES

| Path | Purpose |
| --- | --- |
| `.apseudo-lint.toml` | Linter/formatter configuration. |
| `.apseudo/scripts.toml` | Optional executable task registry. |
| `.apseudo/runs/` | Recommended persistent run-record root. |
| `.pre-commit-config.yaml` | Local Git enforcement. |
| `.github/workflows/apseudo-lint.yml` | CI enforcement. |
| `integrations/agent-hooks/apseudo-hook.py` | Shared Claude/Codex hook implementation. |
| `.claude/settings.json` | Claude Code hook configuration. |
| `.codex/hooks.json` | Codex hook configuration. |
| `.mcp.json` | MCP server registration. |
| `products/vscode-extension/` | VS Code grammar, LSP client, snippets, and packaged extension assets. |
| `products/kate-integration/` | Kate syntax and LSP integration docs/config. |

## EXAMPLES

### Validate the project

```bash
uv run apseudo lint .
uv run apseudo format --check .
uv run apseudo review .
```

### Preview a runner prompt

```bash
uv run apseudo run --codex --render-prompt fix-ruff -- target=src
```

### Execute a registered runner script with audit output

```bash
uv run apseudo run --codex --apply \
  --run-dir .apseudo/runs \
  --post-check "uv run pytest" \
  fix-ruff -- target=src
```

### Check provider setup

```bash
uv run apseudo doctor --json
```

### Generate agent task docs

```bash
uv run apseudo docs generate --output docs/apseudo-docs/usage/agent-tasks.md
```

## NOTES

- The unified `apseudo` command is for humans. The standalone commands are stable for CI, hooks, editor integrations, and scripts.
- `apseudo-run` is an agent launcher, not a deterministic interpreter.
- Prefer `--render-prompt`, `--print-command`, and `--check` before trusting new executable pseudocode.
- For repository gates, use pre-commit and CI in addition to agent hooks.

## SEE ALSO

- [`docs/apseudo-docs/usage/RUNNER-USAGE.md`](RUNNER-USAGE.md)
- [`docs/reference/EXECUTABLE-PSEUDOCODE-SPEC.md`](../../reference/EXECUTABLE-PSEUDOCODE-SPEC.md)
- [`docs/apseudo-docs/usage/AGENT-INSTRUCTIONS-WORDING.md`](AGENT-INSTRUCTIONS-WORDING.md)
- [`docs/apseudo-docs/roadmap/FUTURE-VERSIONS.md`](../roadmap/FUTURE-VERSIONS.md)
