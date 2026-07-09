# Runner Workflows

Date: 2026-07-09  
Applies to: Agent Pseudocode Toolkit `0.6.1`

## What the runner does

`apseudo-run` makes a pseudocode file callable like a script.

It does not execute the pseudocode directly. It performs a deterministic wrapper flow:

```text
read executable .apseudo
    ↓
parse shebang and frontmatter
    ↓
validate with apseudo-lint
    ↓
resolve args, workspace, provider, and mode
    ↓
render a strict agent prompt
    ↓
launch claude -p or codex exec
    ↓
require structured outcome
    ↓
run deterministic post-checks
    ↓
write run records and exit with predictable status
```

## Minimum executable script

```text
#!/usr/bin/env apseudo-run
---
name: review_spec
description: Review a spec without modifying files.
default_agent: claude
mode: review
workspace: git_root
requires_clean_git: false
args:
  spec_path:
    type: path
    required: true
    description: Specification file to review.
---

process review_spec(spec_path):
    spec = read_file(spec_path)

    if spec is None:
        return Blocked(reason="spec file could not be read")

    review = review_document(spec)

    if review.blockers:
        return Blocked(reason="review blockers found", evidence=review.summary)

    else:
        return Accepted(reason="no blockers found")
```

Save as:

```text
docs/apseudo-docs/examples/runner/review-spec.apseudo
```

Then run:

```bash
uv run apseudo-run --claude --review docs/apseudo-docs/examples/runner/review-spec.apseudo -- spec_path=docs/reference/PYTHONIC_PSEUDOCODE_STANDARD.md
```

## Safe first-run sequence

Use this sequence before letting a script edit a repo.

### 1. Validate the script

```bash
uv run apseudo-run --check docs/apseudo-docs/examples/runner/fix-ruff.apseudo
```

### 2. Show script-specific help

```bash
uv run apseudo-run docs/apseudo-docs/examples/runner/fix-ruff.apseudo --help
```

### 3. Render the exact prompt

```bash
uv run apseudo-run --codex --render-prompt docs/apseudo-docs/examples/runner/fix-ruff.apseudo -- target=src
```

### 4. Print the provider command

```bash
uv run apseudo-run --codex --print-command docs/apseudo-docs/examples/runner/fix-ruff.apseudo -- target=src
```

### 5. Run in review/plan mode first

```bash
uv run apseudo-run --codex --review \
  --require-no-diff \
  --run-dir .apseudo/runs \
  docs/apseudo-docs/examples/runner/fix-ruff.apseudo -- target=src
```

### 6. Run in apply mode with post-checks

```bash
uv run apseudo-run --codex --apply \
  --run-dir .apseudo/runs \
  --post-check "uv run ruff check src tests integrations/agent-hooks" \
  --post-check "uv run pytest" \
  docs/apseudo-docs/examples/runner/fix-ruff.apseudo -- target=src
```

## Run records

Use `--run-dir` for anything non-trivial.

```bash
uv run apseudo-run --codex --apply \
  --run-dir .apseudo/runs \
  docs/apseudo-docs/examples/runner/fix-ruff.apseudo -- target=src
```

Expected run directory contents:

```text
.apseudo/runs/<run-id>/
├── manifest.json
├── script.apseudo
├── rendered-prompt.md
├── agent-command.json
├── stdout.log
├── stderr.log
├── events.jsonl
├── outcome.json
├── final-message.md
├── changed-files.txt
├── git-diff.patch
└── validation-after.json
```

Use run records when:

- the task may take many turns;
- the result matters for auditability;
- you want to compare Claude versus Codex behavior;
- you need to debug a failed headless run;
- you plan to include evidence in an issue or PR.

## Registered tasks

Use the registry for recurring tasks.

Registry:

```text
.apseudo/scripts.toml
```

Run by name:

```bash
uv run apseudo run fix-ruff --codex --apply -- target=src
uv run apseudo run review-spec --claude --review -- spec_path=docs/reference/PYTHONIC_PSEUDOCODE_STANDARD.md
```

Generate task docs:

```bash
uv run apseudo docs generate --output docs/apseudo-docs/usage/agent-tasks.md
```

Use registered tasks when the repo has a known set of repeatable agent actions.

## Script arguments

Prefer declared arguments in frontmatter:

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
    description: Treat warnings as failures.
```

Then pass values after `--`:

```bash
uv run apseudo-run --codex script.apseudo -- target=src strict=true
```

or with `--set`:

```bash
uv run apseudo-run --codex script.apseudo --set target=src --set strict=true
```

Use an argument file for longer inputs:

```bash
uv run apseudo-run --codex script.apseudo --arg-file .apseudo/args/fix-docs.yml
```

## Diff policy

Use diff policy to keep mode honest.

Review-only task:

```bash
uv run apseudo-run --claude --review --require-no-diff script.apseudo
```

Apply task expected to change files:

```bash
uv run apseudo-run --codex --apply --expect-diff script.apseudo
```

This catches mismatches such as:

- a review script that accidentally edits files;
- an apply script that reports success but changes nothing.

## Post-checks

Post-checks run outside the model loop.

```bash
uv run apseudo-run --codex --apply script.apseudo \
  --post-check "uv run apseudo-lint ." \
  --post-check "uv run pytest" \
  --post-check "uv run pyright"
```

Use post-checks for deterministic verification that should not depend on the agent remembering to run commands.

## Provider choice

Use Claude for high-level review:

```bash
uv run apseudo-run --claude --review script.apseudo
```

Use Codex for repo edits:

```bash
uv run apseudo-run --codex --apply script.apseudo
```

Override the executable when testing wrappers:

```bash
uv run apseudo-run --codex --agent-command ./tests/fake-codex script.apseudo
```

## Hermetic versus project context

Use project context when you want the repo's `AGENTS.md`, `CLAUDE.md`, hooks, skills, and MCP behavior to matter:

```bash
uv run apseudo-run --codex --project-context script.apseudo
```

Use hermetic mode for reproducible CI-like runs:

```bash
uv run apseudo-run --codex --hermetic script.apseudo
```

Hermetic mode should be more explicit and less dependent on local user configuration.

## Danger mode

`--danger` is intentionally hard to use.

Do not put danger behavior in frontmatter as a normal default. Use it only in disposable environments.

```bash
uv run apseudo-run --codex --danger --i-understand-danger script.apseudo
```

For most cross-directory tasks, prefer `--add-dir` over danger mode:

```bash
uv run apseudo-run --codex --apply \
  --add-dir ../template-repo \
  standards/processes/sync-template-repo.apseudo
```

## Replay and resume

Inspect a saved run:

```bash
uv run apseudo-run --replay .apseudo/runs/<run-id>
```

Rerun using the saved script snapshot:

```bash
uv run apseudo-run --rerun .apseudo/runs/<run-id>
```

Resume when provider metadata supports it:

```bash
uv run apseudo-run --resume-run .apseudo/runs/<run-id>
```

Use replay/rerun/resume for long-running or failed agent tasks where preserving context matters.

## Troubleshooting checklist

Run doctor:

```bash
uv run apseudo doctor --codex
uv run apseudo doctor --claude
```

Run provider test:

```bash
uv run apseudo provider-test --json
```

Check validation:

```bash
uv run apseudo-lint .
uv run apseudo-review .
```

Print prompt and command:

```bash
uv run apseudo-run --render-prompt --print-command --codex script.apseudo -- arg=value
```

If a real provider run fails, inspect the run directory first. The prompt and command there are the most useful debugging artifacts.
