# apseudo-run

Date: 2026-07-09  
Applies to: Agent Pseudocode Toolkit `0.6.1`

## NAME

`apseudo-run` — validate an executable Agent Pseudocode script, feed it to headless Claude Code or Codex CLI, capture a run record, and return a shell-usable outcome.

## SYNOPSIS

```text
apseudo-run [AGENT] [MODE] [OPTIONS] <script.apseudo> [-- <key=value>...]
<script.apseudo> [AGENT] [MODE] [OPTIONS] [-- <key=value>...]
apseudo-claude [MODE] [OPTIONS] <script.apseudo> [-- <key=value>...]
apseudo-codex [MODE] [OPTIONS] <script.apseudo> [-- <key=value>...]
apseudo-run --schema
apseudo-run --replay <run-dir> [--json]
apseudo run [AGENT] [MODE] [OPTIONS] <script-or-registry-name> [-- <key=value>...]
```

## DESCRIPTION

`apseudo-run` makes `.apseudo` files usable as executable agent task launchers. It does **not** execute pseudocode directly. It performs this deterministic wrapper flow:

1. Parse optional shebang and frontmatter.
2. Validate the pseudocode body with `apseudo-lint` rules.
3. Resolve script arguments, defaults, workspace, agent, mode, and provider options.
4. Render a strict prompt containing the pseudocode and outcome schema.
5. Launch Claude Code or Codex CLI in headless/non-interactive mode.
6. Require a structured final outcome: `Accepted`, `Blocked`, or `NeedsUserDecision`.
7. Optionally run deterministic post-check commands.
8. Optionally enforce Git diff policy.
9. Write run records, events, logs, outcome files, diffs, and changed-file lists.
10. Return a predictable shell exit code.

Use the runner for repeatable AI-assisted workflows that require judgment and repository edits, such as lint repair, bounded spec review, docs repair, issue triage, and template synchronization. Use Bash or Python instead for deterministic operations such as file moves, secret rotation, backups, production deploys, or irreversible infrastructure actions.

**Relationship to `apseudo run`:** `apseudo-run` is the standalone `[project.scripts]` entry point that owns the full option contract documented on this page. `apseudo run` (a leaf command of the unified `apseudo` dispatcher — see [`usage.md`](usage.md)) is a thin front end over it: it resolves a script argument that is either a filesystem path or a `.apseudo/scripts.toml` registry name, then delegates to `apseudo-run` with the resolved path. The two accept the same `[AGENT] [MODE] [OPTIONS]` surface; `apseudo run` adds only registry-name resolution on top. `apseudo-claude` and `apseudo-codex` are further standalone aliases that pin `apseudo-run`'s agent selection to `claude` or `codex` respectively. Unified equivalent: `apseudo run` runs this entry point after resolving the script argument.

## EXECUTABLE SCRIPT FORMAT

A script may include a shebang and frontmatter before the normal Agent Pseudocode body:

```text
#!/usr/bin/env apseudo-run
---
name: fix_ruff_failures
description: Fix Ruff failures in a bounded, verified loop.
default_agent: codex
mode: apply
workspace: git_root
requires_clean_git: false
args:
  target:
    type: path
    required: false
    default: .
    description: Path to run Ruff against.
codex:
  sandbox: workspace-write
claude:
  bare: false
  allowed_tools:
    - Read
    - Edit
    - Bash
---

process fix_ruff_failures(target="."):
    diagnostics = run_command("uv run ruff check {target}")

    if diagnostics.empty:
        return Accepted(reason="ruff already passes")

    for diagnostic in diagnostics:  # @finite_collection
        fix_diagnostic(diagnostic)
        targeted_result = run_command("uv run ruff check {diagnostic.file}")

        if targeted_result.failed:
            return Blocked(reason="targeted Ruff check still fails", evidence=targeted_result.output)

    final_result = run_command("uv run ruff check {target}")

    if final_result.passed:
        return Accepted(reason="all Ruff failures fixed")

    return Blocked(reason="full Ruff check still fails", evidence=final_result.output)
```

Run it directly after marking it executable:

```bash
chmod +x docs/apseudo-docs/examples/runner/fix-ruff.apseudo
docs/apseudo-docs/examples/runner/fix-ruff.apseudo --codex --apply -- target=src
```

## QUICK START

### Validate a runner script

```bash
uv run apseudo-run --check docs/apseudo-docs/examples/runner/fix-ruff.apseudo
```

### Show script-specific help

```bash
uv run apseudo-run docs/apseudo-docs/examples/runner/fix-ruff.apseudo --help
```

### Render the exact agent prompt

```bash
uv run apseudo-run --codex --render-prompt docs/apseudo-docs/examples/runner/fix-ruff.apseudo -- target=src
```

### Preview the external provider command

```bash
uv run apseudo-run --codex --print-command docs/apseudo-docs/examples/runner/fix-ruff.apseudo -- target=src
```

### Run with Codex and persist a run record

```bash
uv run apseudo-run --codex --apply \
  --run-dir .apseudo/runs \
  --post-check "uv run ruff check src" \
  --output .apseudo/latest-outcome.json \
  docs/apseudo-docs/examples/runner/fix-ruff.apseudo -- target=src
```

### Run with Claude in review mode

```bash
uv run apseudo-run --claude --review \
  --require-no-diff \
  docs/apseudo-docs/examples/runner/review-spec.apseudo -- spec_path=docs/specs/PYTHONIC_PSEUDOCODE_STANDARD.md
```

### Use the unified command and script registry

```bash
uv run apseudo run --codex --apply fix-ruff -- target=src
uv run apseudo docs generate --output docs/apseudo-docs/usage/agent-tasks.md
```

## OPTIONS

### Agent selection

#### `--claude`

Run the script with Claude Code headless/print mode.

#### `--codex`

Run the script with Codex CLI non-interactive `exec` mode.

#### `--agent <agent>`

Select `claude` or `codex` explicitly. Resolution order is CLI flag, `APSEUDO_AGENT`, script `default_agent`, then configuration error.

### Actions

#### `--check`

Validate the script body and argument metadata. Does not render a prompt or launch an agent.

#### `--render-prompt`

Print the exact prompt that would be sent to the selected agent.

#### `--print-command`

Print the external provider command without running it. Use `--json` for argv/cwd/schema-path details.

#### `--schema`

Print the runner's final outcome JSON Schema.

#### `--replay <run-dir>`

Read a saved run directory and print the manifest summary.

#### `--rerun <run-dir>`

Re-run the script snapshot saved in a run directory. The runner uses `script.apseudo` from the run directory when present.

#### `--resume-run <run-dir>`

Resume the run using provider session metadata when available. This is best-effort because provider session IDs depend on provider output.

### Execution mode

#### `--plan`, `--review`, `--apply`, `--danger`

Override the script's `mode`. `plan` and `review` are read-oriented. `apply` permits workspace edits through provider tools/sandboxing. `danger` requires `--i-understand-danger` and is intended only for isolated disposable environments.

### Workspace and safety

#### `--workspace <path>`

Override the workspace root. Script frontmatter defaults to `git_root`.

#### `--require-clean-git`

Require a clean Git worktree before launch.

#### `--allow-dirty`

Allow a dirty worktree when a clean worktree would otherwise be required.

#### `--require-no-diff`

Fail after the run if Git shows changes. Use for review/plan scripts that must not mutate the workspace.

#### `--expect-diff`

Fail after the run if Git shows no changes. Use for apply scripts that should modify files.

#### `--lock <name>`

Acquire `.apseudo/locks/<name>.lock` before running, then remove it on exit. Use this to prevent concurrent agent runs against the same workspace.

### Provider options

#### `--agent-command <command>`

Override the provider executable path/name. Useful for tests, wrappers, or local aliases.

#### `--model <model>`

Pass a model override to the selected provider when supported.

#### `--profile <profile>`

Pass a Codex profile override.

#### `--sandbox <policy>`

Pass a Codex sandbox policy. Common values: `read-only`, `workspace-write`, `danger-full-access`.

#### `--approval-policy <policy>`

Provider-neutral approval intent. Values: `untrusted`, `on-request`, `never`, `auto-approved-tools`. For Codex, compatible values map to `--ask-for-approval`. For Claude, the runner maps the intent to permission/tool configuration where practical.

#### `--add-dir <path>`

Grant or reference an additional directory. For Codex, this maps to repeated `--add-dir` flags. For Claude, the path is included in the execution prompt as an additional workspace constraint.

#### `--ephemeral`

Request provider non-persistence where supported.

#### `--hermetic`

Prefer explicit runner-supplied context over provider auto-discovery. For Codex this adds `--ignore-user-config`; for Claude this forces `--bare`.

#### `--project-context`

Prefer repository/provider context such as `CLAUDE.md`, `AGENTS.md`, hooks, MCP config, and skills where supported.

#### `--resume <session-id>`

Resume a specific provider session where supported.

#### `--resume-last`

Resume or continue the most recent provider session where supported.

#### `--resume-all`

Allow broader provider session search where supported.

### Claude-specific options

#### `--claude-bare`

Force Claude Code `--bare` mode.

#### `--claude-project`

Force Claude project-context mode and disable frontmatter `bare: true`.

#### `--allowed-tool <tool>`

Add a Claude allowed tool entry. Repeatable.

#### `--max-turns <n>`

Pass a Claude Code maximum turn count.

#### `--max-budget-usd <amount>`

Pass a Claude Code maximum budget.

### Output, logging, and run records

#### `--run-dir <path>`

Create a persistent run record under `<path>/<timestamp>-<script>-<agent>-<id>/`.

Run record contents include:

```text
manifest.json
script.apseudo
rendered-prompt.md
agent-command.json
stdout.log
stderr.log
final-message.txt
outcome.json
post-checks.json
changed-files.txt
git-diff.patch
validation-before.json
validation-after.json
events.jsonl
hook-audit.jsonl  # when hooks run inside this runner context
```

#### `--output <file>`

Write the normalized final outcome to a file.

#### `--output-last-message <file>`

Write the provider final message to a file. Codex receives this path directly; Claude output is captured and written by the runner.

#### `--events <file>`

Write JSONL runner/provider events to a file. When `--run-dir` is set and `--events` is omitted, the run directory gets `events.jsonl`.

#### `--stream`

Stream provider output to the terminal while capturing it. Claude uses streaming JSON output settings; Codex uses JSON event output.

#### `--prompt-out <file>`

Write the rendered prompt before execution.

#### `--schema-out <file>`

Write the generated outcome schema before execution.

#### `--changed-files-out <file>`

Write post-run Git changed files.

#### `--diff-out <file>`

Write post-run Git diff patch.

#### `--outcome-format {json,markdown,text}`

Select stdout and `--output` format. Default: `json`.

#### `--quiet`

Suppress successful outcome printing. Errors still go to stderr.

#### `--verbose`

Reserved for additional runner detail in future provider adapters.

### Arguments and variables

#### `--set <key=value>`

Set a script argument before positional `-- key=value` values are applied.

#### `--arg-file <path>`

Load script arguments from a JSON object or simple YAML-like key/value file.

#### `--vars <path>`

Alias for `--arg-file`; intended for prompt-variable files.

### Deterministic verification

#### `--post-check <command>`

Run a shell command after the provider exits. Repeatable. Any non-zero post-check changes the final outcome to `Blocked`.

#### `--fail-on-warning`

Treat linter warnings as validation failure.

### Hooks and MCP expectations

#### `--require-hooks`

Fail when the selected provider's project hook config is absent. The runner checks file presence; provider trust state still needs to be managed inside Claude Code or Codex.

#### `--no-hooks`

Request hook/rule bypass where supported. This is intentionally visible in the prompt and safety logic and should be rare.

#### `--require-mcp`

Fail when `.mcp.json` is absent in the workspace.

### Process control

#### `--timeout-seconds <n>`

Kill the provider process after the timeout.

#### `--timeout-idle-seconds <n>`

Reserved idle-output timeout option. It is accepted for policy compatibility; current adapters enforce total timeout only.

#### `--max-output-bytes <n>`

Limit captured stdout/stderr per stream.

#### `--retry <n>`

Retry provider process failures up to `n` times. Validation failures, safety failures, schema failures, post-check failures, and diff-policy failures are not retried.

## SCRIPT REGISTRY

A repository may register named tasks in `.apseudo/scripts.toml`:

```toml
[scripts.fix-ruff]
path = "docs/apseudo-docs/examples/runner/fix-ruff.apseudo"
description = "Fix Ruff failures in a bounded, verified loop."
default_agent = "codex"
default_mode = "apply"
```

Run registered scripts through the unified CLI:

```bash
uv run apseudo run --codex --apply fix-ruff -- target=src
```

Generate task documentation from the registry:

```bash
uv run apseudo docs generate --output docs/apseudo-docs/usage/agent-tasks.md
```

## EXIT STATUS

| Code | Meaning |
| ---: | --- |
| `0` | `Accepted` — script completed and verification passed. |
| `10` | `NeedsUserDecision` — explicit user input or approval is required. |
| `20` | `Blocked` — script could not complete or verification failed. |
| `30` | Local pseudocode validation failed. |
| `31` | Runner configuration, argument, registry, or repeat-run metadata error. |
| `40` | Provider command failed. |
| `41` | Provider output did not match the required outcome schema. |
| `50` | Safety policy blocked execution. |

## ENVIRONMENT

| Variable | Meaning |
| --- | --- |
| `APSEUDO_AGENT` | Default agent when no CLI flag or script `default_agent` is set. Allowed values: `claude`, `codex`. |
| `APSEUDO_RUN_ID` | Set by the runner for provider subprocesses when `--run-dir` is active. |
| `APSEUDO_RUN_DIR` | Set by the runner for provider subprocesses when `--run-dir` is active. Hooks use this to write run-local audit records. |
| `PYTHONPATH` | Used by source-tree wrapper scripts under `scripts/`. |

## FILES

| Path | Purpose |
| --- | --- |
| `.apseudo/scripts.toml` | Optional registry of named executable pseudocode tasks. |
| `.apseudo/runs/` | Recommended run-record root. |
| `.apseudo/locks/` | Workspace lock files created by `--lock`. |
| `.claude/settings.json` | Claude Code hook/project configuration checked by `--require-hooks`. |
| `.codex/hooks.json` | Codex hook/project configuration checked by `--require-hooks`. |
| `.mcp.json` | MCP configuration checked by `--require-mcp`. |

## EXAMPLES

### Run a safe read-only review and guarantee no diff remains

```bash
uv run apseudo-run --claude --review \
  --require-no-diff \
  --run-dir .apseudo/runs \
  docs/apseudo-docs/examples/runner/review-spec.apseudo -- spec_path=docs/specs/PYTHONIC_PSEUDOCODE_STANDARD.md
```

### Run an apply task and require it to make a change

```bash
uv run apseudo-run --codex --apply \
  --expect-diff \
  --post-check "uv run pytest" \
  docs/apseudo-docs/examples/runner/fix-ruff.apseudo -- target=src
```

### Run with persistent artifacts for audit/debugging

```bash
uv run apseudo-run --codex --apply \
  --run-dir .apseudo/runs \
  --output .apseudo/latest/outcome.json \
  --output-last-message .apseudo/latest/final-message.json \
  --events .apseudo/latest/events.jsonl \
  --changed-files-out .apseudo/latest/changed-files.txt \
  --diff-out .apseudo/latest/git-diff.patch \
  docs/apseudo-docs/examples/runner/fix-ruff.apseudo -- target=src
```

### Resume the last provider session

```bash
uv run apseudo-run --claude --resume-last docs/apseudo-docs/examples/runner/review-spec.apseudo -- spec_path=docs/specs/PYTHONIC_PSEUDOCODE_STANDARD.md
uv run apseudo-run --codex --resume-last docs/apseudo-docs/examples/runner/fix-ruff.apseudo -- target=src
```

### Re-play a saved run record

```bash
uv run apseudo-run --replay .apseudo/runs/20260709T010203Z-fix-ruff-codex-a1b2c3d4
```

### Use a script argument file

```json
{
  "target": "src",
  "strict": true
}
```

```bash
uv run apseudo-run --codex --apply --arg-file args.json docs/apseudo-docs/examples/runner/fix-ruff.apseudo
```

### Run a cross-repository task with extra write directories

For a local cross-repo script named `sync-template.apseudo`:

```bash
uv run apseudo-run --codex --apply \
  --add-dir ../project-standards \
  --add-dir ../template-repo \
  sync-template.apseudo -- template=../template-repo
```

## NOTES

- `apseudo-run` is an agent launcher, not a deterministic interpreter.
- Hooks, pre-commit, CI, and post-checks remain the hard enforcement layer.
- `--render-prompt` and `--print-command` are the safest way to review new scripts before execution.
- `--danger` and `danger-full-access` should be limited to disposable VMs or throwaway worktrees.
- The runner writes structured JSONL events and manifest files instead of depending on a specific logging library. When `structlog` is installed, internal runner logging can use it; otherwise the toolkit falls back to stdlib JSON logging.

## SEE ALSO

- `docs/specs/EXECUTABLE-PSEUDOCODE-SPEC.md` — normative executable script specification.
- `docs/apseudo-docs/usage/AGENT-INSTRUCTIONS-WORDING.md` — copy/paste wording for repositories.
- `docs/apseudo-docs/roadmap/FUTURE-VERSIONS.md` — future runner and system roadmap.
- `docs/apseudo-docs/usage/usage.md` — overall CLI usage reference.
