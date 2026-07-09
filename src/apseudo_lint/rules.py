"""Rule catalog for Pythonic Agent Pseudocode.

The linter emits compact APSEUDO-* codes. This catalog is the canonical
explanation layer used by the CLI, LSP hovers/code actions, MCP tools, and
documentation generation. Keeping the rule text here prevents each integration
from inventing its own wording.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Rule:
    """Human-facing metadata for one validator rule."""

    code: str
    title: str
    severity: str
    summary: str
    rationale: str
    compliant_example: str
    noncompliant_example: str
    fix: str
    source: str = "Internal convention"

    def as_markdown(self) -> str:
        """Render the rule as Markdown."""

        return f"""### {self.code}: {self.title}

- **Default severity:** {self.severity}
- **Source:** {self.source}

{self.summary}

**Rationale:** {self.rationale}

**Non-compliant:**

```text
{self.noncompliant_example.rstrip()}
```

**Compliant:**

```text
{self.compliant_example.rstrip()}
```

**Fix:** {self.fix}
""".rstrip()


RULES: dict[str, Rule] = {
    "APSEUDO-IO-001": Rule(
        code="APSEUDO-IO-001",
        title="File must be valid UTF-8",
        severity="error",
        summary="Supported pseudocode and Markdown files must be readable as UTF-8.",
        rationale="Agent-facing standards should be portable across local editors, CI, and remote agents.",
        noncompliant_example="<non UTF-8 bytes>",
        compliant_example="# UTF-8 encoded pseudocode\nprocess demo():\n    return Accepted()",
        fix="Re-save the file as UTF-8.",
    ),
    "APSEUDO-IO-002": Rule(
        code="APSEUDO-IO-002",
        title="Input path must exist",
        severity="error",
        summary="Explicit files passed to the linter must exist.",
        rationale="Missing files usually indicate a broken hook, stale CI path, or mistyped command.",
        noncompliant_example="apseudo-lint docs/missing.apseudo",
        compliant_example="apseudo-lint docs/process.apseudo",
        fix="Correct the path or remove the stale reference.",
    ),
    "APSEUDO-NORM-001": Rule(
        code="APSEUDO-NORM-001",
        title="Normative keywords must be uppercase",
        severity="warning",
        summary="Use uppercase RFC-style normative terms: MUST, MUST NOT, SHOULD, SHOULD NOT, MAY, REQUIRED, OPTIONAL.",
        rationale="Uppercase normative keywords make hard requirements visually distinct from ordinary prose.",
        noncompliant_example="# agent should run tests",
        compliant_example="# agent SHOULD run tests",
        fix="Run apseudo-format or uppercase the normative term manually.",
        source="RFC 2119-inspired internal convention",
    ),
    "APSEUDO-NORM-002": Rule(
        code="APSEUDO-NORM-002",
        title="Use MUST/SHOULD/MAY instead of SHALL",
        severity="warning",
        summary="The standard avoids SHALL and SHALL NOT to keep the vocabulary small.",
        rationale="Agents and reviewers get more consistent signal from one compact normative vocabulary.",
        noncompliant_example="# agent SHALL stop on blockers",
        compliant_example="# agent MUST stop on blockers",
        fix="Replace SHALL with MUST, and SHALL NOT with MUST NOT.",
        source="Internal convention",
    ),
    "APSEUDO-PARSE-001": Rule(
        code="APSEUDO-PARSE-001",
        title="Block header must use the standard shape",
        severity="error",
        summary="Process, branch, loop, and exception headers must follow their Pythonic pseudocode forms and end with a colon.",
        rationale="The validator and agents rely on Python-shaped block headers to identify structure.",
        noncompliant_example="if approved\n    return Accepted()",
        compliant_example="if approved:\n    return Accepted()",
        fix="Add the missing colon or rewrite the header using the documented block form.",
        source="Python compound-statement-inspired internal convention",
    ),
    "APSEUDO-PARSE-002": Rule(
        code="APSEUDO-PARSE-002",
        title="Block header must have an indented body",
        severity="error",
        summary="Every block header must be followed by at least one indented executable line unless explicitly allowed.",
        rationale="Empty branches are ambiguous instructions for agents.",
        noncompliant_example="if approved:\nreturn Accepted()",
        compliant_example="if approved:\n    return Accepted()",
        fix="Indent the body, add a real action, or annotate an intentionally empty branch with @allow_empty_branch.",
    ),
    "APSEUDO-PROC-001": Rule(
        code="APSEUDO-PROC-001",
        title="Full workflow block should declare a process",
        severity="warning",
        summary="Standalone workflow snippets should start with process name(...): or def name(...): unless configured otherwise.",
        rationale="Named processes are addressable by agents, language-server symbols, templates, and generated diagrams.",
        noncompliant_example="review = review_document(document)\nreturn Accepted()",
        compliant_example="process review_document_flow(document):\n    review = review_document(document)\n    return Accepted()",
        fix="Wrap the snippet in a process declaration or add @allow_missing_process for a fragment.",
    ),
    "APSEUDO-RETURN-001": Rule(
        code="APSEUDO-RETURN-001",
        title="Process must have a terminal return outcome",
        severity="error",
        summary="Every process must return at least one approved outcome.",
        rationale="Agents need explicit success/failure outcomes to know when the workflow is complete.",
        noncompliant_example="process demo():\n    do_work()",
        compliant_example="process demo():\n    do_work()\n    return Accepted(reason=\"done\")",
        fix="Add a terminal return such as Accepted(...), Blocked(...), or NeedsUserDecision(...).",
    ),
    "APSEUDO-RETURN-002": Rule(
        code="APSEUDO-RETURN-002",
        title="Return must use an outcome value",
        severity="warning",
        summary="Bare return statements and arbitrary return values are discouraged.",
        rationale="Outcome constructors make termination states explicit and searchable.",
        noncompliant_example="return",
        compliant_example="return Blocked(reason=\"missing required input\")",
        fix="Return an approved outcome constructor or add a project outcome to the config.",
    ),
    "APSEUDO-RETURN-003": Rule(
        code="APSEUDO-RETURN-003",
        title="Process should end with an explicit terminal statement",
        severity="warning",
        summary="The final executable line in a process should be return, raise, break, or continue.",
        rationale="A non-terminal trailing action can make completion ambiguous.",
        noncompliant_example="process demo():\n    do_work()\n    verify_work()",
        compliant_example="process demo():\n    do_work()\n    verify_work()\n    return Accepted(reason=\"verified\")",
        fix="Append an explicit return outcome or justify the non-return terminal action.",
    ),
    "APSEUDO-OUTCOME-001": Rule(
        code="APSEUDO-OUTCOME-001",
        title="Returned outcome must be approved",
        severity="warning",
        summary="Returned outcome names must appear in the configured allowed outcome set.",
        rationale="A finite outcome vocabulary lets agents, hooks, and reports classify process endings consistently.",
        noncompliant_example="return Done()",
        compliant_example="return Accepted(reason=\"done\")",
        fix="Use an approved outcome or add the intentional project-specific outcome to .apseudo-lint.toml.",
    ),
    "APSEUDO-WHILE-001": Rule(
        code="APSEUDO-WHILE-001",
        title="While loop must have a bounded stop condition",
        severity="error",
        summary="while loops must include a cap, timeout, deadline, maximum counter, or explicit bounded annotation.",
        rationale="Unbounded loops are one of the highest-risk failure modes for autonomous agents.",
        noncompliant_example="while not approved:\n    revise(document)",
        compliant_example="while not approved and round <= max_rounds:\n    revise(document)\n    round += 1",
        fix="Add a bounded condition, update loop state, or annotate a genuine external stop condition.",
    ),
    "APSEUDO-WHILE-002": Rule(
        code="APSEUDO-WHILE-002",
        title="While body should update loop-control state",
        severity="warning",
        summary="A while loop should visibly mutate state used by the condition or terminate from inside the loop.",
        rationale="A bounded-looking loop can still be infinite if its condition never changes.",
        noncompliant_example="while round <= max_rounds:\n    revise(document)",
        compliant_example="while round <= max_rounds:\n    revise(document)\n    round += 1",
        fix="Update the condition variable, return/break from the loop, or annotate an external stop condition.",
    ),
    "APSEUDO-WHILE-003": Rule(
        code="APSEUDO-WHILE-003",
        title="while True must visibly terminate",
        severity="error",
        summary="while True requires an explicit annotation and a visible break, return, or raise in the loop body.",
        rationale="Intentional infinite loops are exceptional and must document their exit path.",
        noncompliant_example="while True:\n    poll_queue()",
        compliant_example="# @intentional_infinite_loop until shutdown_requested\nwhile True:\n    if shutdown_requested:\n        return Accepted(reason=\"shutdown\")",
        fix="Prefer a bounded while condition; otherwise annotate and add a reachable terminal statement.",
    ),
    "APSEUDO-FOR-001": Rule(
        code="APSEUDO-FOR-001",
        title="For loop iterable should be visibly bounded",
        severity="warning",
        summary="for loops should iterate over a named collection, literal collection, range, or annotated bounded source.",
        rationale="Unclear generator/call expressions can hide unbounded or side-effectful work.",
        noncompliant_example="for item in fetch_items():\n    process_item(item)",
        compliant_example="items = fetch_items(limit=max_items)\nfor item in items:\n    process_item(item)",
        fix="Name the collection, use range/literal data, or add @bounded/@finite_collection.",
    ),
    "APSEUDO-BRANCH-001": Rule(
        code="APSEUDO-BRANCH-001",
        title="if/elif chain should have fallback",
        severity="warning",
        summary="Non-terminal if/elif chains should include else or be annotated @exhaustive.",
        rationale="Fallback branches prevent silent no-op behavior when a condition is unexpected.",
        noncompliant_example="if approved:\n    return Accepted()",
        compliant_example="if approved:\n    return Accepted()\nelse:\n    return Blocked(reason=\"not approved\")",
        fix="Add else with an explicit action/outcome, or annotate @exhaustive when the condition set is complete.",
    ),
    "APSEUDO-BRANCH-002": Rule(
        code="APSEUDO-BRANCH-002",
        title="Placeholder body should be resolved",
        severity="warning",
        summary="A branch body containing only pass or ... is considered incomplete.",
        rationale="Placeholders are easy for agents to skip accidentally.",
        noncompliant_example="else:\n    pass",
        compliant_example="else:\n    return Blocked(reason=\"unsupported state\")",
        fix="Replace the placeholder or mark the branch with @allow_empty_branch.",
    ),
    "APSEUDO-NEST-001": Rule(
        code="APSEUDO-NEST-001",
        title="Nesting should stay shallow",
        severity="warning",
        summary="Nesting deeper than the configured maximum should be refactored.",
        rationale="Deeply nested agent instructions are harder for humans and models to follow reliably.",
        noncompliant_example="if a:\n    if b:\n        if c:\n            if d:\n                if e:\n                    return Accepted()",
        compliant_example="if not a:\n    return Blocked(reason=\"a missing\")\nif not b:\n    return Blocked(reason=\"b missing\")\nreturn Accepted()",
        fix="Use guard clauses, helper processes, or decision tables.",
    ),
    "APSEUDO-ACTION-001": Rule(
        code="APSEUDO-ACTION-001",
        title="Mutating action should be followed by verification",
        severity="warning",
        summary="Mutating actions should be followed by verify/check/test/review or a terminal outcome.",
        rationale="Agent workflows should not silently assume that a change succeeded.",
        noncompliant_example="write_file(path, content)\nreturn Accepted()",
        compliant_example="write_file(path, content)\nverify_file(path)\nreturn Accepted()",
        fix="Add a verification action or @no_verification_required with rationale.",
    ),
    "APSEUDO-ACTION-002": Rule(
        code="APSEUDO-ACTION-002",
        title="Action names should use lower_snake_case",
        severity="warning",
        summary="Agent action/function calls should use lower_snake_case unless they are outcome constructors.",
        rationale="Consistent action names improve completions, search, and rename behavior.",
        noncompliant_example="ReviewDocument(document)",
        compliant_example="review_document(document)",
        fix="Rename the action to lower_snake_case.",
    ),
}


def get_rule(code: str) -> Rule | None:
    """Return rule metadata for a code, if known."""

    return RULES.get(code)


def list_rules() -> list[Rule]:
    """Return rules sorted by code."""

    return [RULES[code] for code in sorted(RULES)]
