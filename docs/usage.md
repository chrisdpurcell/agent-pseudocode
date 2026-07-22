---
schema_version: '1.1'
id: 'reference-000001-cli-usage'
title: 'apseudo CLI Usage'
description: 'Command-line reference for the apseudo toolkit: linting, formatting, review, Mermaid rendering, and the executable pseudocode runner.'
doc_type: 'reference'
status: 'active'
created: '2026-07-22'
updated: '2026-07-22'
tags:
  - 'cli'
aliases: []
related:
  - 'docs/reference/PYTHONIC_PSEUDOCODE_STANDARD.md'
  - 'docs/reference/RULES.md'
---

# apseudo

## NAME

`apseudo` — validate, format, review, visualize, and execute Pythonic Agent Pseudocode.

## SYNOPSIS

```bash
apseudo <command> [<args>...]
apseudo {--help | --version}

apseudo-lint [OPTIONS] [<paths>...]
apseudo-format [OPTIONS] [<paths>...]
apseudo-run [OPTIONS] <script.apseudo> [-- <key=value>...]
```

## DESCRIPTION

`apseudo` is the umbrella command for the Agent Pseudocode toolkit. It validates `.apseudo`, `.agentpseudo`, and `.pseudocode` files, plus `apseudo`-fenced blocks inside Markdown, against the APSEUDO-\* rule catalog.

The validator and formatter are the policy source of truth. The language server, MCP server, agent hooks, pre-commit hooks, CI, and editor integrations all reuse those modules rather than reimplementing rules, so a diagnostic means the same thing everywhere it appears.

Every subcommand is also installed as a standalone entry point (`apseudo lint` and `apseudo-lint` are equivalent). The standalone forms carry the full option surface and are what hooks and CI invoke; `apseudo <command>` is the convenience front door.

Most commands read from standard input when no path is given, and write diagnostics to standard error and primary output to standard output.

### Commands

| Command | Standalone | Purpose |
| --- | --- | --- |
| `lint` | `apseudo-lint` | Validate files and Markdown fenced blocks against the rule catalog. |
| `format` | `apseudo-format` | Normalize indentation, blank lines, and normative keywords. |
| `review` | `apseudo-review` | Repository-level convention and tooling completeness checks. |
| `mermaid` | `apseudo-mermaid` | Render a process as a Mermaid flowchart view. |
| `run` | `apseudo-run` | Execute an executable `.apseudo` script through Claude Code or Codex. |
| `replay` | — | Summarize a saved runner run directory. |
| `doctor` | — | Report local provider and tool availability. |
| `provider-test` | — | Fake-provider runner smoke test. |
| `docs generate` | — | Generate Markdown docs for registered executable scripts. |
| — | `apseudo-explain` | Explain APSEUDO-\* rules and convention guidance. |
| — | `apseudo-template` | List or emit starter pseudocode templates. |
| — | `apseudo-lsp` | Language server (stdio). |
| — | `apseudo-mcp` | MCP server (stdio). |

`apseudo-claude` and `apseudo-codex` are thin wrappers that pin `apseudo-run` to one agent backend.

## OPTIONS

### Common to `apseudo-lint` and `apseudo-format`

#### `--config <file>`

Use an explicit configuration file instead of discovery.

Default: the nearest `.apseudo-lint.toml`, `apseudo.toml`, or `pyproject.toml`, searched upward from each target.

#### `--changed`

Restrict the run to Git-changed supported files.

Default: off. This is what the repository's pre-commit hooks use.

#### `--stdin-filename <path>`

Process standard input as though it came from `<path>`, so extension-based and config-based behavior still applies.

#### `--quiet`

Suppress success output. Diagnostics are still reported.

### `apseudo-lint`

#### `--format <fmt>`

Select the diagnostic output format.

Allowed values: `text`, `json`, `github`. Use `github` to emit GitHub Actions annotations.

Default: `text`.

#### `--strict`

Treat warnings as failures.

#### `--fail-on-warnings`

Treat warnings as failures without enabling other strict behavior.

#### `--errors-only`

Suppress warnings and infos in both output and the failure calculation.

### `apseudo-format`

#### `--check`

Exit non-zero if any file needs formatting. Writes nothing.

#### `--diff`

Print unified diffs for files that would change. Writes nothing.

#### `--write`

Write formatted output. This is the default unless `--check` or `--diff` is given.

#### `--indent-size <n>`

Indent width in spaces.

Default: 4, matching the `.editorconfig` rule for pseudocode and Python files.

#### `--max-blank-lines <n>`

Maximum consecutive blank lines to preserve.

#### `--round-indentation`

Round leading indentation to multiples of `--indent-size`.

Default: off, because rounding can silently reindent a block whose nesting was already meaningful.

#### `--no-uppercase-normative`

Leave normative keywords (`MUST`, `SHOULD`, `MAY`) in comments as written instead of uppercasing them.

### `apseudo-run`

The runner has a large option surface; `apseudo-run --help` is authoritative. The options that matter before trusting a new or edited script:

#### `--check`

Validate the script and print diagnostics only. No agent is invoked.

#### `--render-prompt`

Print the exact prompt that would be sent to the agent.

#### `--print-command`

Print the external agent command without running it.

#### `--claude`, `--codex`, `--agent <name>`

Select the agent backend.

Default: `APSEUDO_AGENT`, then the config file's `default_agent`. With none of these set, the runner refuses to guess and exits with a configuration error.

#### `--mode <mode>` (`--plan`, `--review`, `--apply`, `--danger`)

Execution mode. `--danger` additionally requires `--i-understand-danger`.

Default: the script's declared mode.

Safety: prefer `--plan` or `--review` before `--apply` for any new or safety-sensitive script.

#### `--run-dir <dir>`

Write an auditable run record. Prefer `--run-dir .apseudo/runs`.

#### `--require-clean-git`, `--allow-dirty`

Require or waive a clean Git workspace before executing.

#### `--require-no-diff`, `--expect-diff`, `--post-check <cmd>`

Post-run assertions on the resulting working tree.

## EXIT STATUS

`apseudo`, `apseudo-lint`, `apseudo-format`, `apseudo-review`, and the other non-runner commands:

| Code | Meaning                          |
| ---- | -------------------------------- |
| `0`  | Success; no failing diagnostics  |
| `1`  | Failing diagnostics found        |
| `2`  | Usage error or invalid arguments |

`apseudo-run` reports the script's terminal outcome as a distinct code, so a blocked run is not confused with a crash:

| Code | Meaning                                        |
| ---- | ---------------------------------------------- |
| `0`  | `Accepted`                                     |
| `10` | `NeedsUserDecision`                            |
| `20` | `Blocked`                                      |
| `30` | Script validation failed                       |
| `31` | Configuration invalid                          |
| `40` | Agent invocation failed                        |
| `41` | Agent output did not match the expected schema |
| `50` | Safety gate blocked the run                    |

## ENVIRONMENT

- `APSEUDO_AGENT` — default runner backend (`claude` or `codex`) when no `--claude`, `--codex`, or `--agent` is given.
- `NO_COLOR` — disable ANSI color output.

## FILES

- `.apseudo-lint.toml`, `apseudo.toml`, or `[tool.apseudo_lint]` in `pyproject.toml` — configuration, discovered upward from each target in that order.
- `.apseudo/scripts.toml` — registry of named executable scripts.
- `.apseudo/runs/` — run records written by `--run-dir`.

## EXAMPLES

### Validate the repository

```bash
apseudo lint .
```

### Check formatting without writing

```bash
apseudo format --check .
```

### Lint only what changed, as CI annotations

```bash
apseudo-lint --changed --format github
```

### Understand a diagnostic

```bash
apseudo-explain APSEUDO-WHILE-001
```

### Start from a template

```bash
apseudo-template --list
apseudo-template bounded-review-loop > review-loop.apseudo
```

### Inspect an executable script before trusting it

```bash
apseudo-run --check review-loop.apseudo
apseudo-run --render-prompt review-loop.apseudo -- target=src
apseudo-run --print-command review-loop.apseudo -- target=src
```

### Execute with an audit trail

```bash
apseudo-run --codex --review --run-dir .apseudo/runs review-loop.apseudo -- target=src
```

### Render a diagram without ANSI color

```bash
NO_COLOR=1 apseudo mermaid docs/reference/language/examples/review-loop.apseudo --no-fence > flow.mmd
```

## NOTES

- The validator and formatter define policy. If an editor, hook, or CI check disagrees with `apseudo-lint`, the tooling is wrong, not the file.
- `--check` and `--diff` never write; `apseudo-format` writes only in its default mode or with an explicit `--write`.
- Do not bypass hooks, pre-commit, CI, runner post-checks, or diff policy to make a run pass.

## SEE ALSO

- `docs/reference/PYTHONIC_PSEUDOCODE_STANDARD.md` — the convention itself.
- `docs/reference/RULES.md` — the full APSEUDO-\* rule catalog.
- `docs/adr/README.md` — architecture decision records.
