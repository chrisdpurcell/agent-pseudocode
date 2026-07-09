# Executable Agent Pseudocode Specification

Date: 2026-07-09  
Applies to: Agent Pseudocode Toolkit `0.6.1`  
Status: Internal convention

## 1. Purpose

Executable Agent Pseudocode turns a validated `.apseudo` process into a command-line task launcher. The file is executable in the Unix sense, but the pseudocode body is **not interpreted as code**. The runner validates the process, renders it into a constrained agent prompt, launches Claude Code or Codex CLI, and validates the provider's final outcome.

## 2. Script envelope

An executable script MAY begin with a shebang:

```text
#!/usr/bin/env apseudo-run
```

A script MAY include YAML-like frontmatter between `---` delimiters. The parser intentionally supports a small metadata subset: top-level `key: value`, one-level nested maps, and simple lists.

```apseudo
# !/usr/bin/env apseudo-run
---
name: example
description: Demonstrate executable pseudocode.
default_agent: codex
mode: review
workspace: git_root
---

process example():
    return Accepted(reason="ok")
```

The pseudocode body begins after the closing frontmatter delimiter. The body follows the Pythonic Agent Pseudocode Standard and is validated exactly like standalone `.apseudo` files.

## 3. Frontmatter fields

| Field | Type | Required | Meaning |
| --- | --- | ---: | --- |
| `name` | string | no | Human-readable script/process name. |
| `description` | string | no | One-line user-facing purpose. |
| `default_agent` | `claude` or `codex` | no | Agent selected when no CLI flag or `APSEUDO_AGENT` is set. |
| `mode` | `plan`, `review`, `apply`, `danger` | no | Default execution mode. Default: `plan`. |
| `workspace` | `git_root`, `cwd`, `script_dir`, or path | no | Workspace root. Default: `git_root`. |
| `requires_clean_git` | bool | no | Require a clean Git worktree before launch. |
| `allow_dirty_git` | bool | no | Allow dirty worktree even when clean is required. |
| `args` | map | no | Script argument schema. |
| `claude` | map | no | Claude-specific defaults. |
| `codex` | map | no | Codex-specific defaults. |

## 4. Argument schema

The optional `args` map declares script-level arguments. Each argument MAY declare:

| Field | Meaning |
| --- | --- |
| `type` | `string`, `path`, `int`, `integer`, `float`, `number`, `bool`, or `boolean`. |
| `required` | When true, the runner fails before rendering if the value is absent. |
| `default` | Default value applied before prompt rendering. |
| `description` | User-facing description used in script-specific help. |
| `allowed_values` / `choices` | Optional list of accepted values. |

Example:

```yaml
args:
  target:
    type: path
    required: false
    default: .
    description: Path to operate on.
  strict:
    type: bool
    required: false
    default: false
```

Argument resolution order:

1. Argument files from `--arg-file` / `--vars`.
2. Re-run metadata when using `--rerun` / `--resume-run`.
3. CLI `--set key=value` values.
4. Values after `--`, such as `target=src`.
5. Frontmatter defaults.

The runner validates required arguments and coerces declared types before rendering the prompt.

## 5. Agent selection

Agent resolution order:

1. `--claude`, `--codex`, or `--agent`.
2. `APSEUDO_AGENT`.
3. Frontmatter `default_agent`.
4. Configuration error.

## 6. Execution modes

| Mode | Intended use | Default provider posture |
| --- | --- | --- |
| `plan` | Proposal only | read-oriented |
| `review` | Analysis/review | read-oriented |
| `apply` | Workspace edits | edit-capable within sandbox/tool limits |
| `danger` | Explicit high-risk run | requires `--i-understand-danger` |

`danger` MUST NOT be selected implicitly by a script alone. The operator must pass `--i-understand-danger`.

## 7. Provider mapping

### Claude

The runner builds a `claude -p` command. It supplies the rendered prompt, requests JSON output, supplies the runner outcome schema through `--json-schema`, and sets tool/permission options from CLI/frontmatter where available.

Claude-specific frontmatter keys include:

```yaml
claude:
  bare: false
  allowed_tools:
    - Read
    - Edit
    - Bash
  output_format: json
  max_turns: 8
  max_budget_usd: 2.0
  permission_mode: acceptEdits
```

### Codex

The runner builds a `codex exec` command. It passes the rendered prompt through stdin with `-`, writes/passes an outcome schema, requests JSON events, and captures the final message.

Codex-specific frontmatter keys include:

```yaml
codex:
  sandbox: workspace-write
  model: gpt-5.5-codex
  profile: default
  approval_policy: never
  skip_git_repo_check: false
  add_dir:
    - ../other-repo
```

## 8. Prompt contract

Every rendered prompt includes:

- toolkit version;
- script path;
- selected agent;
- execution mode;
- workspace;
- frontmatter metadata;
- resolved script arguments;
- runner policy flags;
- allowed terminal outcomes;
- the JSON outcome schema;
- the pseudocode body.

The final provider response MUST be a JSON object matching the outcome schema.

## 9. Outcome schema

Required fields:

```json
{
  "outcome": "Accepted | Blocked | NeedsUserDecision",
  "reason": "short reason",
  "summary": "human-readable summary",
  "checks_run": ["check command or check label"],
  "artifacts": ["path or URL"]
}
```

Optional field:

```json
{
  "evidence": "supporting output or reason"
}
```

Exit-code mapping:

| Outcome / condition | Exit code |
| --- | ---: |
| `Accepted` | `0` |
| `NeedsUserDecision` | `10` |
| `Blocked` | `20` |
| validation failed | `30` |
| config invalid | `31` |
| provider failed | `40` |
| output invalid | `41` |
| safety blocked | `50` |

## 10. Run records

When `--run-dir <path>` is set, the runner creates a per-run directory containing the script snapshot, rendered prompt, command JSON, validation results, provider logs, final outcome, Git diff, changed-file list, events, and hook audit records.

Required record files:

```text
manifest.json
script.apseudo
rendered-prompt.md
agent-command.json
validation-before.json
events.jsonl
```

Files created when relevant:

```text
stdout.log
stderr.log
final-message.txt
outcome.json
post-checks.json
changed-files.txt
git-diff.patch
validation-after.json
hook-audit.jsonl
```

## 11. Deterministic post-run checks

`--post-check <command>` is outside the agent loop. The runner executes each command after provider completion. A non-zero post-check changes the normalized result to `Blocked` even when the provider returned `Accepted`.

Use post-checks for tests, formatters, linters, spec validators, and repository review commands.

## 12. Diff policy

`--require-no-diff` fails when Git has changes after the run. Use it for read-only review/plan scripts.

`--expect-diff` fails when Git has no changes after the run. Use it for apply scripts expected to modify files.

The policy checks Git status after completion. For precise before/after semantics, combine with `--require-clean-git`.

## 13. Hooks and MCP

`--require-hooks` checks for the selected provider's project hook configuration file. It does not prove provider-side trust/approval. Provider trust remains an operator responsibility.

`--require-mcp` checks that `.mcp.json` exists in the workspace.

When `--run-dir` is active, the runner sets `APSEUDO_RUN_ID` and `APSEUDO_RUN_DIR` for the provider subprocess. The included hook script writes run-local audit entries to `hook-audit.jsonl` when these variables are present.

## 14. Script registry

A repository MAY include `.apseudo/scripts.toml`:

```toml
[scripts.fix-ruff]
path = "docs/examples/runner/fix-ruff.apseudo"
description = "Fix Ruff failures in a bounded, verified loop."
default_agent = "codex"
default_mode = "apply"
```

The unified command can resolve registered names:

```bash
apseudo run --codex --apply fix-ruff -- target=src
```

## 15. Logging

The normative audit artifact is the run directory, especially JSON files and JSONL event streams. Internal process logging uses `structlog` when it is installed; otherwise it falls back to stdlib JSON logging. The toolkit does not require `structlog` at runtime.

## 16. Compatibility and limits

- Executable pseudocode is a runner convention, not an operating-system interpreter language.
- Provider flags are best-effort mappings across different CLI semantics.
- The runner does not guarantee that an agent followed every pseudocode branch; it validates the script, constrains the prompt, captures the outcome, and enforces deterministic wrapper checks.
- Use CI and repository hooks as the final hard gate.
