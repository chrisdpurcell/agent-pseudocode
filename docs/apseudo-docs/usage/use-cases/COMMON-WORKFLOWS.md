# Common Workflows and Use Cases

Date: 2026-07-09  
Applies to: Agent Pseudocode Toolkit `0.6.1`

## Use case map

| Workflow | Best surface | Agent usually selected | Why |
| --- | --- | --- | --- |
| Spec review loop | Standalone `.apseudo` or Markdown fence | Claude for design review, Codex for implementation review | Needs bounded loops and blockers. |
| Fix lint/type/test failures | Executable runner script | Codex | Needs repo edits plus verification. |
| Handoff size control | Standalone `.apseudo` referenced by standards | Either | Prevents guess-and-check shrinking. |
| Upstream bug reporting | Standalone `.apseudo` | Either | Requires consistent issue/trace handling. |
| Release gate | Standalone `.apseudo` plus hooks | Either | Needs explicit approval and failure paths. |
| Template repo sync | Executable runner script | Codex | Needs cross-repo inspection and PR creation. |
| Documentation repair | Executable runner script | Codex | Needs edits plus docs validation. |
| Policy audit | Runner script in review mode | Claude | Needs analysis without mutation. |

## 1. Bounded spec review

Use Agent Pseudocode when Claude/Codex review loops must stop after a fixed number of rounds.

```apseudo
process review_spec(spec, reviewer, max_rounds=5):
    round = 1
    blockers = []

    while round <= max_rounds:
        review = reviewer.review(spec)

        if review.status == "approved":
            return Accepted(reason="spec approved")

        elif review.blockers:
            blockers = review.blockers
            spec = revise_using_blockers(spec, blockers)
            round += 1
            continue

        else:
            return Blocked(reason="ambiguous review output")

    return Blocked(reason="round cap reached", unresolved_blockers=blockers)
```

How it gets used:

```text
Prompt the agent: Follow standards/processes/review-spec.apseudo. Stop after the round cap and surface unresolved blockers.
```

Why pseudocode helps:

- prevents infinite revision loops;
- preserves blockers across rounds;
- defines approved, ambiguous, and capped outcomes.

## 2. Fix Ruff failures

Use an executable runner script because the workflow needs edits and verification.

Existing example:

```text
docs/apseudo-docs/examples/runner/fix-ruff.apseudo
```

Command:

```bash
uv run apseudo run fix-ruff --codex --apply \
  --run-dir .apseudo/runs \
  --post-check "uv run ruff check src tests integrations/agent-hooks" \
  --post-check "uv run pytest" \
  --expect-diff \
  -- target=src
```

Why pseudocode helps:

- the agent must verify each fix;
- the runner records prompt, command, output, logs, changed files, and diff;
- post-checks run outside the model loop.

When not to use it:

- when `ruff --fix` alone is sufficient;
- when the change is deterministic and no agent judgment is required.

## 3. Handoff size control

Use this when agents repeatedly guess how much to shorten a document.

```apseudo
process prepare_handoff(document, max_chars, max_rounds=3):
    round = 1
    measured_chars = count_chars(document)

    while measured_chars > max_chars and round <= max_rounds:
        excess_chars = measured_chars - max_chars
        target_reduction = excess_chars + 500
        document = reduce_document(document, target_reduction=target_reduction)
        measured_chars = count_chars(document)
        round += 1

    if measured_chars <= max_chars:
        return Accepted(reason="handoff within limit")

    else:
        return Blocked(reason="handoff still exceeds limit", measured_chars=measured_chars)
```

How it gets used:

```text
Before producing a handoff, follow standards/processes/handoff-size-control.apseudo. Measure first; do not guess reductions.
```

Why pseudocode helps:

- requires measurement before editing;
- computes target reduction;
- limits rounds;
- blocks instead of repeatedly guessing.

## 4. Upstream bug reporting

Use this when repo A encounters a bug in repo B, and both are in your GitHub inventory.

```apseudo
process report_upstream_bug(source_repo, upstream_repo, bug_evidence):
    if upstream_repo is None:
        return Blocked(reason="upstream repository is unknown")

    if bug_evidence is None:
        return Blocked(reason="bug evidence is missing")

    upstream_issue = create_issue(repo=upstream_repo, evidence=bug_evidence)
    tracking_issue = create_issue(repo=source_repo, upstream_issue=upstream_issue)

    return Accepted(reason="upstream issue and tracking issue created")
```

How it gets used:

```text
If you identify an upstream bug, follow standards/processes/report-upstream-bug.apseudo. Create both the upstream issue and the local tracking issue.
```

Why pseudocode helps:

- avoids burying upstream bugs in local workarounds;
- creates traceability in both repositories;
- stops when the upstream repo or evidence is missing.

## 5. Release gate

Use this when an agent may merge, tag, publish, or release.

```apseudo
process release_gate(change_set, ci_result, approval_required=True):
    if ci_result.status != "passed":
        return Blocked(reason="CI did not pass")

    if approval_required:
        approval = ask_user_inline(question="Approve release?", options=["approve", "reject"])

        if approval != "approve":
            return NeedsUserDecision(reason="release not approved")

    publish_release(change_set)
    return Accepted(reason="release completed")
```

How it gets used:

```text
Do not release by GitHub UI approval. Ask for inline approval and follow standards/processes/release-gate.apseudo.
```

Why pseudocode helps:

- makes CI status mandatory;
- requires inline approval;
- prevents external manual UI steps from being treated as part of the agent workflow.

## 6. Template repository sync

Use this when a standards release should update a template repository.

```apseudo
process sync_template_repo(standard_release, template_repo):
    if standard_release.status != "published":
        return Blocked(reason="standard release is not published")

    changes = compute_template_delta(source=standard_release.artifacts, target=template_repo)

    if changes.empty:
        return Accepted(reason="template already matches standard release")

    apply_changes(template_repo, changes)
    validation = run_template_validation(template_repo)

    if validation.failed:
        return Blocked(reason="template validation failed", evidence=validation.output)

    open_pull_request(repo=template_repo, title="Sync template with standard release")
    return Accepted(reason="template sync PR opened")
```

How it gets used:

```bash
uv run apseudo-run --codex --apply \
  --add-dir ../project-template \
  --run-dir .apseudo/runs \
  standards/processes/sync-template-repo.apseudo -- release=2026-07-09
```

Why pseudocode helps:

- works across repositories;
- computes drift before applying changes;
- validates before opening the PR;
- stops when standards are not published.

## 7. Documentation repair

Use this when docs require many small edits but need validation after changes.

```apseudo
process repair_docs(paths, max_rounds=3):
    round = 1

    while round <= max_rounds:
        result = run_command("uv run apseudo-lint {paths}")

        if result.passed:
            return Accepted(reason="docs validate")

        elif result.findings:
            fix_doc_findings(result.findings)
            round += 1
            continue

        else:
            return Blocked(reason="validation output is ambiguous")

    return Blocked(reason="round cap reached")
```

Command:

After saving the workflow as `repair-docs.apseudo`:

```bash
uv run apseudo-run --codex --apply \
  --post-check "uv run apseudo-lint docs" \
  --post-check "uv run apseudo-format --check docs" \
  repair-docs.apseudo -- paths=docs
```

Why pseudocode helps:

- keeps the agent from broad, uncontrolled rewriting;
- requires validation after changes;
- stops after repeated failures.

## 8. Policy audit

Use review mode when you want an agent to inspect but not modify.

Command:

```bash
uv run apseudo-run --claude --review \
  --require-no-diff \
  --run-dir .apseudo/runs \
  docs/apseudo-docs/examples/runner/review-spec.apseudo -- spec_path=docs/reference/PYTHONIC_PSEUDOCODE_STANDARD.md
```

Why pseudocode helps:

- the runner enforces no-diff behavior;
- Claude can analyze the document without editing;
- the run record captures the prompt and final result.

## Choosing Claude or Codex

Recommended defaults:

| Task | Default |
| --- | --- |
| Spec critique, policy review, tradeoff analysis | Claude |
| Repository edits, tests, lint/type repair | Codex |
| Cross-checking another agent's output | Opposite model from the author |
| CLI/script repair | Codex |
| Standards language review | Claude first, Codex second |

The runner supports both providers. Use flags to override script defaults:

```bash
uv run apseudo-run --claude --review script.apseudo
uv run apseudo-run --codex --apply script.apseudo
```
