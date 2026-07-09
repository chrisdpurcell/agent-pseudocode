# agent-pseudocode-syntax-toolkit

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

Default output: `docs/usage/agent-tasks.md`.

## EXIT STATUS

| Code | Meaning |
| ---: | --- |
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

| Variable | Meaning |
| --- | --- |
| `APSEUDO_AGENT` | Default executable runner agent: `claude` or `codex`. |
| `APSEUDO_RUN_ID` | Set inside provider subprocesses when `--run-dir` is active. |
| `APSEUDO_RUN_DIR` | Set inside provider subprocesses when `--run-dir` is active. |
| `PYTHONPATH` | Used by source-tree wrapper scripts under `scripts/`. |

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
uv run apseudo docs generate --output docs/usage/agent-tasks.md
```

## NOTES

- The unified `apseudo` command is for humans. The standalone commands are stable for CI, hooks, editor integrations, and scripts.
- `apseudo-run` is an agent launcher, not a deterministic interpreter.
- Prefer `--render-prompt`, `--print-command`, and `--check` before trusting new executable pseudocode.
- For repository gates, use pre-commit and CI in addition to agent hooks.

## SEE ALSO

- [`docs/usage/RUNNER-USAGE.md`](RUNNER-USAGE.md)
- [`docs/specs/EXECUTABLE-PSEUDOCODE-SPEC.md`](EXECUTABLE-PSEUDOCODE-SPEC.md)
- [`docs/usage/AGENT-INSTRUCTIONS-WORDING.md`](AGENT-INSTRUCTIONS-WORDING.md)
- [`docs/roadmap/FUTURE-VERSIONS.md`](FUTURE-VERSIONS.md)
