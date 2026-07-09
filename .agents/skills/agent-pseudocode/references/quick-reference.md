# Agent Pseudocode Quick Reference

## Canonical flow shape

```apseudo
process workflow_name(input, max_rounds=5) -> Outcome:
    round = 1

    while round <= max_rounds:
        result = perform_action(input)
        verify_result(result)

        if result.accepted:
            return Accepted(reason="verified")

        elif result.blockers:
            input = revise_using_blockers(input, result.blockers)
            round += 1
            continue

        else:
            return Blocked(reason="ambiguous result")

    return Blocked(reason="round cap reached")
```

## Required checks

- `while` loops need a cap, timeout, deadline, counter, or documented external stop condition.
- `for` loops need a visibly finite iterable.
- `if` / `elif` chains need an `else` fallback unless annotated `@exhaustive`.
- Full workflows should use `process name(...):` and approved outcomes.
- Mutating actions should be followed by verification when `require_verification_after_mutation` is enabled.

## Approved outcomes

`Accepted`, `Approved`, `Blocked`, `Deferred`, `Failed`, `NeedsInput`, `NeedsUserDecision`, `OpenIssue`, `Rejected`, `Skipped`.

## Diagnostic triage

- Use `scripts/apseudo-explain <CODE>` for rule intent and examples.
- Use `scripts/apseudo-format --check --changed` before linter runs.
- Use `scripts/apseudo-review .` for project completeness.
