"""Reusable Agent Pseudocode templates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Template:
    """A named template exposed through CLI, LSP completions, and MCP."""

    name: str
    title: str
    description: str
    body: str


TEMPLATES: dict[str, Template] = {
    "bounded-review-loop": Template(
        name="bounded-review-loop",
        title="Bounded review/revision loop",
        description="Review a document until approval, blockers, or a round cap.",
        body='''process review_until_accepted(document, reviewer, max_rounds=5) -> Outcome:
    round = 1
    blockers = []

    while round <= max_rounds:
        review = reviewer.review(document)

        if review.status == "approved":
            return Accepted(reason="review approved")

        elif review.status == "rejected" and review.blockers:
            blockers = review.blockers
            document = revise_document(document, blockers)
            verify_document(document)
            round += 1
            continue

        else:
            return Blocked(reason="ambiguous review result")

    return Blocked(reason="round cap reached", unresolved_blockers=blockers)
''',
    ),
    "guarded-process": Template(
        name="guarded-process",
        title="Guard-clause process",
        description="Validate inputs up front, then execute and verify the main action.",
        body='''process perform_guarded_action(required_input, max_attempts=3) -> Outcome:
    if required_input is None:
        return NeedsInput(reason="required_input is missing")

    attempt = 1

    while attempt <= max_attempts:
        result = perform_action(required_input)
        verify_result(result)

        if result.accepted:
            return Accepted(reason="verified result")

        attempt += 1

    return Blocked(reason="max attempts reached")
''',
    ),
    "decision-fallback": Template(
        name="decision-fallback",
        title="Explicit decision fallback",
        description="Branch on known states and block on unexpected state.",
        body='''process route_by_status(item) -> Outcome:
    status = classify_status(item)

    if status == "ready":
        process_ready_item(item)
        verify_item(item)
        return Accepted(reason="ready item processed")

    elif status == "needs_input":
        return NeedsUserDecision(reason="additional user input required")

    elif status == "skip":
        return Skipped(reason="item intentionally skipped")

    else:
        return Blocked(reason="unsupported status", status=status)
''',
    ),
    "for-each-bounded": Template(
        name="for-each-bounded",
        title="Bounded for-each processing",
        description="Iterate over a named finite collection and carry failures forward.",
        body='''process process_items(items) -> Outcome:
    failures = []

    for item in items:
        result = process_item(item)

        if result.accepted:
            continue

        else:
            failures.append(result)

    if failures:
        return Blocked(reason="one or more items failed", failures=failures)

    else:
        return Accepted(reason="all items processed")
''',
    ),
}


def get_template(name: str) -> Template | None:
    """Return a template by exact name."""

    return TEMPLATES.get(name)


def list_templates() -> list[Template]:
    """Return templates sorted by name."""

    return [TEMPLATES[name] for name in sorted(TEMPLATES)]
