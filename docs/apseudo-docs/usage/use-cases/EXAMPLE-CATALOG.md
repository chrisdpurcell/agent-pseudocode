# Example Catalog

Date: 2026-07-09  
Applies to: Agent Pseudocode Toolkit `0.6.1`

This catalog provides ready-to-adapt examples. Use them as starting points, not as universal policy.

## Pattern: Bounded review loop

Use for specs, plans, docs, and agent handoffs.

```apseudo
process bounded_review(artifact, reviewer, max_rounds=5):
    round = 1
    blockers = []

    while round <= max_rounds:
        review = reviewer.review(artifact)

        if review.status == "approved":
            return Accepted(reason="artifact approved")

        elif review.blockers:
            blockers = review.blockers
            artifact = revise_using_blockers(artifact, blockers)
            round += 1
            continue

        else:
            return Blocked(reason="ambiguous review result")

    return Blocked(reason="round cap reached", unresolved_blockers=blockers)
```

## Pattern: Measure before reducing size

Use for handoff documents and prompt-size caps.

```apseudo
process reduce_to_limit(document, max_chars, max_rounds=3):
    round = 1
    measured_chars = count_chars(document)

    while measured_chars > max_chars and round <= max_rounds:
        excess_chars = measured_chars - max_chars
        target_reduction = excess_chars + 500
        document = reduce_document(document, target_reduction=target_reduction)
        measured_chars = count_chars(document)
        round += 1

    if measured_chars <= max_chars:
        return Accepted(reason="document is within size limit")

    else:
        return Blocked(reason="document still exceeds size limit", measured_chars=measured_chars)
```

## Pattern: Verify after mutation

Use when the agent changes files.

```apseudo
process mutate_then_verify(target, verification_command):
    change_result = apply_change(target)

    if change_result.failed:
        return Blocked(reason="change failed", evidence=change_result.output)

    verification = run_command(verification_command)

    if verification.passed:
        return Accepted(reason="change verified")

    else:
        return Blocked(reason="verification failed", evidence=verification.output)
```

## Pattern: Review-only no-diff task

Use with runner flag `--require-no-diff`.

```apseudo
process review_only(target):
    content = read_file(target)

    if content is None:
        return Blocked(reason="target could not be read")

    findings = analyze_content(content)

    if findings.blockers:
        return Blocked(reason="blockers found", evidence=findings.summary)

    else:
        return Accepted(reason="no blockers found")
```

Command:

```bash
uv run apseudo-run --claude --review --require-no-diff script.apseudo -- target=docs/specs/PYTHONIC_PSEUDOCODE_STANDARD.md
```

## Pattern: Release approval gate

Use before release, tag, publish, or merge actions.

```apseudo
process approval_gate(change_set, ci_result):
    if ci_result.status != "passed":
        return Blocked(reason="CI did not pass")

    approval = ask_user_inline(question="Approve this gated action?", options=["approve", "reject"])

    if approval == "approve":
        perform_gated_action(change_set)
        return Accepted(reason="gated action approved and completed")

    else:
        return NeedsUserDecision(reason="gated action not approved")
```

## Pattern: Cross-repo sync

Use with runner flag `--add-dir` for the extra repo.

```apseudo
process cross_repo_sync(source_repo, target_repo):
    source_state = inspect_repo(source_repo)
    target_state = inspect_repo(target_repo)
    delta = compute_delta(source_state, target_state)

    if delta.empty:
        return Accepted(reason="target already matches source")

    apply_delta(target_repo, delta)
    validation = validate_repo(target_repo)

    if validation.failed:
        return Blocked(reason="target validation failed", evidence=validation.output)

    else:
        return Accepted(reason="target repo synchronized")
```

Command:

```bash
uv run apseudo-run --codex --apply \
  --add-dir ../target-repo \
  --post-check "cd ../target-repo && uv run pytest" \
  script.apseudo -- source_repo=. target_repo=../target-repo
```

## Pattern: Unknown input blocker

Use when the agent must not guess missing details.

```apseudo
process require_input(required_value):
    if required_value is None:
        return NeedsUserDecision(reason="needed input is missing")

    result = use_required_value(required_value)

    if result.passed:
        return Accepted(reason="input used successfully")

    else:
        return Blocked(reason="input use failed", evidence=result.output)
```

## Pattern: Registered runner task

Script frontmatter:

```yaml
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
```

Registry entry:

```toml
[scripts.fix-ruff]
path = "docs/apseudo-docs/examples/runner/fix-ruff.apseudo"
description = "Fix Ruff failures in a bounded, verified loop."
default_agent = "codex"
default_mode = "apply"
```

Command:

```bash
uv run apseudo run fix-ruff --codex --apply -- target=src
```

## Pattern: Agent prompt reference

Use this prompt when a task references a standalone process:

```text
Follow standards/processes/<name>.apseudo as the control-flow source of truth. Preserve loop bounds, guards, fallback branches, and terminal outcomes. If that pseudocode conflicts with prose or implementation details, stop and surface the conflict instead of choosing silently.
```

## Pattern: Completion check prompt

Use this for manual agent runs:

```text
Before completing, run `uv run apseudo-format --check .`, `uv run apseudo-lint .`, and `uv run apseudo-review .`. If any check fails, fix the finding or return Blocked with evidence.
```

## Pattern: Hook-friendly final report

Ask agents to end with this shape when not using `apseudo-run`:

```text
Outcome: Accepted | Blocked | NeedsUserDecision
Checks run:
- <command>
Artifacts changed:
- <path>
Open blockers:
- <blocker or none>
```

When using `apseudo-run`, prefer structured outcome files instead of relying on prose final reports.
