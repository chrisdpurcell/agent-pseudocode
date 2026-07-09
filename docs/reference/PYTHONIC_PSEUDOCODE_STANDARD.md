# Pythonic Pseudocode Standard for AI Agent Instructions

**Version:** 1.0.0  
**Date:** 2026-07-08  
**Status:** Proposed internal convention  
**Audience:** Human authors, AI coding agents, AI reviewers, automation agents  
**Primary use:** Deterministic process instructions, agent workflows, implementation plans, review loops, decision logic, and bounded retry behavior  

---

## Executive Summary

This document defines a comprehensive **Pythonic pseudocode standard** for writing deterministic instructions to AI agents. It is not an official Python standard. It is an internal convention anchored to published Python syntax, Python style guidance, established pseudocode dialects, and requirements-writing practices.

The core recommendation is:

> Use Python-shaped pseudocode for procedural control flow, decision tables for broad condition matrices, explicit outcomes for termination, and RFC-style normative language for rules and invariants.

This standard is designed for instructions that include many `if / elif / else` branches, `for` loops, `while` loops, bounded retries, review cycles, user-approval gates, file changes, GitHub issue/PR workflows, and agent handoffs.

The standard has four major goals:

1. **Readable by humans.** A technically literate reviewer should understand the workflow without mentally compiling a diagram.
2. **Parseable by AI agents.** An agent should be able to follow the control flow without guessing intent from narrative prose.
3. **Deterministic enough for process specs.** Loops, exits, failure paths, state changes, and side effects must be explicit.
4. **Lightweight enough to write quickly.** The author should not need perfect Mermaid, BPMN, or executable Python syntax to express a reliable process.

This document uses source-status labels throughout:

- **[Sourced]** means the concept is directly grounded in a cited public source.
- **[Adapted]** means the concept is derived from a cited source but modified for AI-agent instruction.
- **[Internal Convention]** means this standard defines the rule locally; it should not be represented as an external standard.
- **[Recommendation]** means a best-practice judgment made for this standard.

---

## Table of Contents

1. [Scope](#1-scope)
2. [What This Standard Is and Is Not](#2-what-this-standard-is-and-is-not)
3. [Source Status Legend](#3-source-status-legend)
4. [Foundations and Source Map](#4-foundations-and-source-map)
5. [Normative Language](#5-normative-language)
6. [Design Principles](#6-design-principles)
7. [Document-Level Structure](#7-document-level-structure)
8. [Pseudocode Block Header](#8-pseudocode-block-header)
9. [Lexical and Formatting Rules](#9-lexical-and-formatting-rules)
10. [Naming Conventions](#10-naming-conventions)
11. [Types, Records, and Data Shapes](#11-types-records-and-data-shapes)
12. [Outcomes and Return Values](#12-outcomes-and-return-values)
13. [Process Definitions](#13-process-definitions)
14. [Comments and Docstrings](#14-comments-and-docstrings)
15. [Variables and Assignment](#15-variables-and-assignment)
16. [Boolean Conditions and Comparisons](#16-boolean-conditions-and-comparisons)
17. [Conditional Branching](#17-conditional-branching)
18. [Guard Clauses](#18-guard-clauses)
19. [For Loops](#19-for-loops)
20. [While Loops](#20-while-loops)
21. [Retry Loops](#21-retry-loops)
22. [Break, Continue, and Return](#22-break-continue-and-return)
23. [Error Handling and Blockers](#23-error-handling-and-blockers)
24. [Action Calls and Side Effects](#24-action-calls-and-side-effects)
25. [User Interaction and Approval Gates](#25-user-interaction-and-approval-gates)
26. [External Systems and Tool Use](#26-external-systems-and-tool-use)
27. [Preconditions, Postconditions, and Invariants](#27-preconditions-postconditions-and-invariants)
28. [Decision Tables](#28-decision-tables)
29. [State Transition Tables](#29-state-transition-tables)
30. [Combining Pseudocode, Tables, and Narrative](#30-combining-pseudocode-tables-and-narrative)
31. [Conformance Levels](#31-conformance-levels)
32. [Validation and Lint Rules](#32-validation-and-lint-rules)
33. [Anti-Patterns](#33-anti-patterns)
34. [Worked Examples](#34-worked-examples)
35. [Authoring Workflow](#35-authoring-workflow)
36. [Minimal Adoption Template](#36-minimal-adoption-template)
37. [Reference Cheatsheet](#37-reference-cheatsheet)
38. [Glossary](#38-glossary)
39. [Sources](#39-sources)

---

## 1. Scope

**Source status:** **[Internal Convention]** for agent-specific usage; **[Sourced]** for Python syntax foundations.

This standard governs pseudocode used to instruct AI agents. It applies to:

- Agent workflows.
- Review loops.
- Planning loops.
- Implementation loops.
- File-generation workflows.
- GitHub issue and pull-request workflows.
- Release gates.
- Bounded retry policies.
- Artifact-size reduction loops.
- Decision logic that is too structured for prose but not worth implementing as executable code.
- Human-readable process specs intended to be followed by LLM coding agents.

This standard does **not** govern:

- Production Python code.
- Test code.
- Runtime automation scripts.
- Python package layout.
- API schema definitions.
- Formal verification languages.
- Business process diagrams.
- Mermaid or PlantUML syntax.

When the instruction must be mechanically executed by a computer, write real code. When the instruction must guide an AI agent or human reviewer through structured logic, use this standard.

---

## 2. What This Standard Is and Is Not

**Source status:** **[Internal Convention]**.

### 2.1 This is a local standard

There is no official Python Software Foundation standard named “Python structured pseudocode.” Python has a language reference, style guidance, and type-hinting syntax, but those apply to Python code rather than pseudocode process instructions.

This standard therefore defines a local convention:

```python
# PSEUDOCODE: Python-shaped process instruction, not executable Python.
```

The phrase above is required at the top of non-trivial pseudocode blocks so agents do not overfit to executable Python semantics.

### 2.2 This is Python-shaped, not Python-executable

Pythonic pseudocode borrows from Python:

- Indentation.
- `def` blocks.
- `if / elif / else`.
- `for` loops.
- `while` loops.
- `return`.
- Type-hint-like annotations.
- `snake_case` names.

It intentionally does **not** require:

- Imports.
- Real class definitions.
- Runtime-valid type objects.
- Fully executable function calls.
- Valid package/module context.
- Real exception classes.
- Real object models.

### 2.3 This is a process-spec language

The goal is not to simulate Python. The goal is to express:

- What state exists.
- What conditions are evaluated.
- What actions are required.
- What side effects occur.
- What happens on failure.
- When the process stops.
- What output is expected.

---

## 3. Source Status Legend

**Source status:** **[Internal Convention]**.

Use the following labels when writing or reviewing this standard:

| Label | Meaning | Example |
|---|---|---|
| **[Sourced]** | Directly grounded in an external source | Python `if`, `while`, and `for` are traditional control-flow constructs. |
| **[Adapted]** | Inspired by an external source but modified for this standard | RFC-style MUST/SHOULD terms used outside IETF specs. |
| **[Internal Convention]** | Locally defined rule for this standard | `Blocked(...)` is the required outcome for unresolved agent blockers. |
| **[Recommendation]** | Judgment call made for reliability/readability | Prefer `for attempt in range(...)` over `while True` for retry loops. |

A rule marked **[Internal Convention]** may still be mandatory inside projects that adopt this standard. The label only means the rule should not be misrepresented as an externally published standard.

---

## 4. Foundations and Source Map

**Source status:** Mixed.

This standard is built from the following published foundations and local conventions.

| Area | Source status | Foundation | How this standard uses it |
|---|---|---|---|
| Python block structure | **[Sourced]** | Python Language Reference: compound statements | Uses Python-style indentation, clause headers, colons, and block suites. |
| Python readability | **[Sourced]** | PEP 8 | Uses Python naming and readability conventions where appropriate. |
| Python type notation | **[Sourced]** | PEP 484 and `typing` docs | Allows type-hint-like annotations for clarity, without requiring runtime-valid code. |
| Docstring behavior | **[Sourced]** | PEP 257 | Borrows the idea that summaries, arguments, returns, side effects, and exceptions should be documented. |
| Normative keywords | **[Sourced / Adapted]** | RFC 2119 and RFC 8174 / BCP 14 | Uses uppercase MUST/SHOULD/MAY terms for local requirements. |
| Published pseudocode dialects | **[Sourced]** | AP CSP and Cambridge pseudocode guides | Confirms that structured pseudocode commonly defines assignment, conditionals, loops, procedures, and returns. |
| Requirements syntax | **[Sourced / Adapted]** | EARS | Provides optional natural-language patterns for requirements adjacent to pseudocode. |
| Behavioral examples | **[Sourced / Adapted]** | Gherkin | Provides optional Given/When/Then examples. |
| Decision tables | **[Sourced / Adapted]** | DMN | Supports large condition matrices outside nested `if` blocks. |
| Agent outcomes | **[Internal Convention]** | This standard | Defines `Accepted`, `Blocked`, `NeedsUserDecision`, etc. |
| Agent side-effect semantics | **[Internal Convention]** | This standard | Defines how pseudocode represents file changes, commits, PRs, tool calls, and user questions. |

---

## 5. Normative Language

**Source status:** **[Sourced / Adapted]** from RFC 2119 and RFC 8174.

This document uses uppercase requirement keywords in the style of BCP 14:

- **MUST** and **REQUIRED** indicate mandatory requirements.
- **MUST NOT** indicates mandatory prohibitions.
- **SHOULD** and **RECOMMENDED** indicate strong recommendations where exceptions require justification.
- **SHOULD NOT** indicates discouraged practices where exceptions require justification.
- **MAY** and **OPTIONAL** indicate permitted choices.

RFC 8174 clarifies that the defined requirement meanings apply when the terms are uppercase. This standard follows that convention.

### 5.1 Local use of normative terms

**Source status:** **[Adapted]**.

Although BCP 14 is an IETF convention, this document uses the same keyword style for local process rules. That use is intentional and local.

Example:

```md
- Every `while` loop MUST include a cap, timeout, or explicit stop condition.
- An agent MUST NOT continue after returning `Blocked(...)`.
- A reviewer SHOULD prefer a decision table over deeply nested conditionals.
```

### 5.2 Avoid weak verbs

**Source status:** **[Internal Convention]**.

Avoid weak or ambiguous instruction verbs when writing agent pseudocode.

| Avoid | Prefer |
|---|---|
| try to reduce size | reduce size until `size <= limit` or return `Blocked` |
| make sure tests pass | run tests and require `tests.status == "passed"` |
| handle errors | return `Blocked(reason=..., evidence=...)` |
| if needed | define the condition that makes it needed |
| continue until good | continue until `approved == True` or cap reached |

---

## 6. Design Principles

**Source status:** Mostly **[Internal Convention]**, with readability principles adapted from Python style guidance.

### 6.1 Explicit beats implied

Every process must make these explicit:

- Inputs.
- Outputs.
- Owners or actors.
- Mutable state.
- Branch conditions.
- Loop bounds.
- Stop conditions.
- Side effects.
- Failure outcomes.

Bad:

```python
# PSEUDOCODE
while not done:
    improve_document()
```

Good:

```python
# PSEUDOCODE
for round_number in range(1, max_rounds + 1):
    review = reviewer.review(document)

    if review.status == "approved":
        return Accepted(document=document)

    if review.status == "rejected" and review.blockers:
        document = revise_document(document, review.blockers)
        continue

    return Blocked(reason="ambiguous review result", review=review)

return Blocked(reason="round cap reached", unresolved_blockers=review.blockers)
```

### 6.2 State must be named

Do not rely on vague process memory. Name the state that changes.

Bad:

```python
# PSEUDOCODE
fix_it()
review_again()
```

Good:

```python
# PSEUDOCODE
plan = apply_review_blockers(plan, review.blockers)
review = codex_review(plan)
```

### 6.3 Every loop must have an exit

Every loop MUST terminate by one of these mechanisms:

- Bounded range.
- Explicit maximum attempts.
- Explicit timeout.
- Explicit external stop condition.
- Return on success.
- Return on blocker.

Unbounded loops are prohibited unless the pseudocode is describing a continuously running service, monitor, or daemon and the stop semantics are separately defined.

### 6.4 Failure is an output, not an omission

When the process cannot continue, return a failure outcome. Do not leave failure implied.

```python
# PSEUDOCODE
if missing_required_input:
    return Blocked(
        reason="missing required input",
        missing=["target_repo", "release_type"],
    )
```

### 6.5 Comments cannot carry the only requirement

Comments may explain why. The executable-looking structure must say what.

Bad:

```python
# PSEUDOCODE
# Do not retry forever.
while review_failed:
    revise()
```

Good:

```python
# PSEUDOCODE
for round_number in range(1, max_rounds + 1):
    ...

return Blocked(reason="round cap reached")
```

### 6.6 Prefer flat over deeply nested

Use guard clauses and early returns to keep logic readable.

Bad:

```python
# PSEUDOCODE
if inputs_present:
    if repo_clean:
        if tests_pass:
            release()
        else:
            fix_tests()
    else:
        clean_repo()
else:
    ask_user()
```

Good:

```python
# PSEUDOCODE
if not inputs_present:
    return NeedsUserDecision(question="Provide missing release inputs.")

if not repo_clean:
    return Blocked(reason="repository has uncommitted changes")

if not tests_pass:
    return Blocked(reason="tests failed")

release()
return Accepted(reason="release completed")
```

---

## 7. Document-Level Structure

**Source status:** **[Internal Convention]**.

A process document that uses this standard SHOULD use the following structure.

```md
# Process: <process name>

## Purpose
Explain the outcome in one paragraph.

## Scope
State what the process covers and excludes.

## Actors
List the roles or agents.

## Inputs
List required and optional inputs.

## Outputs
List allowed outcomes and artifacts.

## Pseudocode
Provide the Pythonic pseudocode block.

## Decision Tables
Add tables for broad branching logic.

## Invariants
List requirements that must remain true throughout the process.

## Stop Conditions
List all normal and abnormal exits.

## Acceptance Checks
List checks used to determine completion.

## Examples
Provide concrete examples when behavior could be misunderstood.
```

### 7.1 Required document sections

A conforming document MUST include:

- Purpose.
- Inputs.
- Outputs.
- Pseudocode.
- Stop conditions.

A strict document MUST also include:

- Actors.
- State variables.
- Invariants.
- Decision tables when branching exceeds five cases.
- Worked examples for risky branches.

---

## 8. Pseudocode Block Header

**Source status:** **[Internal Convention]**.

Every non-trivial pseudocode block MUST begin with a sentinel comment.

```python
# PSEUDOCODE: Python-shaped process instruction, not executable Python.
```

The sentinel prevents misinterpretation. It tells agents and humans:

- The syntax is Python-like.
- The block is normative for process behavior.
- The block is not necessarily executable.
- Function calls may represent agent actions rather than real functions.
- Type hints may be descriptive rather than importable.

### 8.1 Minimal valid block

```python
# PSEUDOCODE: Python-shaped process instruction, not executable Python.

def review_document(document: Document, max_rounds: int = 5) -> Outcome:
    for round_number in range(1, max_rounds + 1):
        review = reviewer.review(document)

        if review.approved:
            return Accepted(document=document)

        document = revise_document(document, review.blockers)

    return Blocked(reason="round cap reached")
```

### 8.2 When the sentinel may be omitted

The sentinel MAY be omitted for one-line or two-line examples embedded in prose, but it SHOULD be used for all normative workflow blocks.

---

## 9. Lexical and Formatting Rules

**Source status:** **[Sourced]** from Python indentation and compound-statement conventions; **[Internal Convention]** for pseudocode-specific limits.

Python compound statements use headers and indented suites. This standard borrows that visual structure.

### 9.1 Indentation

Rules:

- Indentation MUST be spaces, not tabs.
- Indentation MUST be consistent within a block.
- Four spaces per indentation level are RECOMMENDED.
- Nested blocks MUST be indented exactly one level deeper than their parent.
- A dedent ends the current block.

Good:

```python
# PSEUDOCODE
def process_item(item: Item) -> Outcome:
    if item.valid:
        process(item)
        return Accepted()

    return Blocked(reason="invalid item")
```

Bad:

```python
# PSEUDOCODE
def process_item(item):
  if item.valid:
       process(item)
        return Accepted()
```

### 9.2 Clause headers

Clause headers SHOULD end with a colon:

```python
if condition:
    action()
```

Because this is pseudocode, a missing colon should not destroy interpretation, but authors MUST write colons in normative standard documents.

### 9.3 Line length

Lines SHOULD be short enough to read in Markdown and terminal contexts. This standard RECOMMENDS a soft line length of 100 characters for pseudocode and 120 characters for tables.

Long calls SHOULD be wrapped vertically:

```python
return Blocked(
    reason="round cap reached",
    unresolved_blockers=review.blockers,
    rounds_attempted=max_rounds,
)
```

### 9.4 Blank lines

Use blank lines to separate conceptual blocks:

```python
review = reviewer.review(document)

if review.approved:
    return Accepted(document=document)

if review.blockers:
    return revise_document(document, review.blockers)
```

Do not use dense, wall-of-text pseudocode.

### 9.5 Code fence language

Use a Markdown code fence labeled `python` for readability and syntax highlighting:

````md
```python
# PSEUDOCODE: Python-shaped process instruction, not executable Python.
...
```
````

If the pseudocode contains many non-Python extensions, use `text` instead of `python`.

---

## 10. Naming Conventions

**Source status:** **[Adapted]** from PEP 8; **[Internal Convention]** for agent-specific names.

### 10.1 General naming

Use Python-style names:

| Thing | Convention | Example |
|---|---|---|
| Variables | `snake_case` | `review_result` |
| Functions/actions | `snake_case` verb phrase | `run_tests()` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_REVIEW_ROUNDS` |
| Types/records/outcomes | `PascalCase` | `ReviewResult` |
| Booleans | Predicate-like names | `has_blockers`, `is_approved` |

### 10.2 Action names

Action calls SHOULD use clear verbs:

```python
run_tests()
review_plan()
revise_document()
create_github_issue()
open_pull_request()
ask_user_for_approval()
```

Avoid vague verbs:

```python
handle()
do_stuff()
fix()
process()
manage()
```

Generic verbs are allowed only when the object makes the action specific:

```python
process_invoice(invoice)
validate_frontmatter(document)
manage_linked_accounts()
```

### 10.3 Agent or actor prefixes

When multiple actors exist, qualify the action:

```python
claude_plan = claude.write_plan(spec)
codex_review = codex.review_plan(claude_plan)
user_decision = user.approve_or_reject(codex_review)
```

This is internal convention. It does not imply real Python objects named `claude`, `codex`, or `user`.

### 10.4 Outcome names

Standard outcome names are `PascalCase`:

```python
Accepted(...)
Blocked(...)
NeedsUserDecision(...)
Rejected(...)
Superseded(...)
Skipped(...)
```

Use a small project-specific outcome vocabulary. Do not create a new outcome for every edge case.

---

## 11. Types, Records, and Data Shapes

**Source status:** **[Sourced / Adapted]** from PEP 484 and Python typing docs; **[Internal Convention]** for pseudocode semantics.

Type hints are allowed because they improve readability, but they are descriptive unless the pseudocode is explicitly intended to be executable.

### 11.1 Function annotations

Use type-hint-like annotations to clarify inputs and outputs:

```python
def amend_document(
    document: MarkdownDocument,
    reviewer: Agent,
    max_rounds: int = 5,
) -> Outcome:
    ...
```

The types need not be importable. They must be understandable.

### 11.2 Optional values

Use `Optional[T]` or `T | None` consistently within a document.

Preferred for pseudocode:

```python
prior_review: ReviewResult | None = None
```

Avoid mixing styles in the same document:

```python
prior_review: Optional[ReviewResult] = None
other_review: ReviewResult | None = None
```

### 11.3 Lists and mappings

Use Python-like collection notation:

```python
blockers: list[Blocker] = []
artifacts: dict[str, Path] = {}
```

If target agents are not expected to understand modern Python type syntax, simplify:

```python
blockers = []  # list of Blocker
artifacts = {}  # map artifact_name -> path
```

### 11.4 Records

Use record-like examples to define expected shapes.

```python
ReviewResult = Record(
    status="approved | rejected | ambiguous",
    blockers=list[Blocker],
    comments=list[str],
)
```

This is internal convention. It is not executable Python unless a project defines `Record`.

### 11.5 Enumerations

Use explicit string enums when states matter:

```python
ReviewStatus = Literal[
    "approved",
    "rejected",
    "ambiguous",
]
```

For simpler documents, list allowed values in prose:

```md
`review.status` MUST be one of: `approved`, `rejected`, `ambiguous`.
```

### 11.6 Unknown or intentionally flexible types

Use `Any` sparingly. PEP 484 defines `Any` as compatible with all types, but in pseudocode it often hides unclear requirements.

Prefer:

```python
raw_tool_result: ToolResult
```

Over:

```python
raw_tool_result: Any
```

---

## 12. Outcomes and Return Values

**Source status:** **[Internal Convention]**.

Agent workflows need explicit terminal states. This standard defines a default outcome vocabulary.

### 12.1 Required terminal outcome categories

Every process MUST eventually return one of these categories or a project-defined equivalent:

| Outcome | Meaning |
|---|---|
| `Accepted(...)` | The process completed successfully and acceptance checks passed. |
| `Blocked(...)` | The process cannot proceed without correction, missing input, or external resolution. |
| `NeedsUserDecision(...)` | The process can continue only after a user decision. |
| `Rejected(...)` | A review or gate explicitly rejected the artifact or action. |
| `Skipped(...)` | The process intentionally did not run because a defined condition made it inapplicable. |
| `Superseded(...)` | The process stopped because a newer artifact, decision, or instruction replaced it. |

### 12.2 Return value content

A terminal outcome SHOULD include enough evidence for the next actor.

Good:

```python
return Blocked(
    reason="round cap reached",
    unresolved_blockers=blockers,
    rounds_attempted=max_rounds,
    next_required_decision="human must decide whether to accept residual risk or revise spec",
)
```

Bad:

```python
return Blocked()
```

### 12.3 Terminal outcomes are final

After `return Accepted(...)`, `return Blocked(...)`, or any other terminal outcome, the process MUST stop. Later pseudocode in the same branch is unreachable and should be removed.

Bad:

```python
return Accepted()
commit_changes()
```

Good:

```python
commit_changes()
return Accepted()
```

### 12.4 Expected failure versus unexpected defect

Use `Blocked(...)` for expected workflow failures:

```python
return Blocked(reason="tests failed", evidence=test_result.failures)
```

Use `SpecificationDefect(...)` or `raise SpecificationDefect(...)` only when the instruction itself is contradictory or incomplete:

```python
return SpecificationDefect(
    reason="process references max_rounds but never defines it",
)
```

`SpecificationDefect` is an internal convention.

---

## 13. Process Definitions

**Source status:** **[Sourced / Adapted]** from Python `def`; **[Internal Convention]** for workflow meaning.

### 13.1 Basic process definition

Use `def` to define a workflow or subroutine:

```python
# PSEUDOCODE: Python-shaped process instruction, not executable Python.

def create_release_pr(repo: Repository, release_type: ReleaseType) -> Outcome:
    ...
```

In this standard, `def` means “define a process that an agent can follow.” It does not require executable Python.

### 13.2 Required process components

A process SHOULD include:

- Inputs.
- Defaults.
- Mutable state.
- Main flow.
- Terminal outcomes.
- Failure handling.

Example:

```python
# PSEUDOCODE: Python-shaped process instruction, not executable Python.

def bounded_review_loop(
    artifact: Artifact,
    reviewer: Agent,
    max_rounds: int = 5,
) -> Outcome:
    blockers: list[Blocker] = []

    for round_number in range(1, max_rounds + 1):
        review = reviewer.review(artifact)

        if review.status == "approved":
            return Accepted(artifact=artifact, rounds=round_number)

        if review.status == "rejected" and review.blockers:
            blockers = review.blockers
            artifact = revise_artifact(artifact, blockers)
            continue

        return Blocked(reason="ambiguous review result", review=review)

    return Blocked(reason="round cap reached", unresolved_blockers=blockers)
```

### 13.3 Subroutines

Use subroutines to hide detail only when the called action is defined elsewhere or self-explanatory.

Acceptable:

```python
review = codex.review_plan(plan)
```

Risky:

```python
result = handle_plan(plan)
```

If a subroutine has complex behavior, define it:

```python
def handle_plan(plan: Plan) -> PlanReviewResult:
    validate_plan_structure(plan)
    verify_acceptance_checks(plan)
    verify_no_unbounded_loops(plan)
    return codex.review_plan(plan)
```

### 13.4 Defaults

Defaults SHOULD be visible at the function signature or in the first lines.

```python
def amend_spec(spec: Spec, max_rounds: int = 5) -> Outcome:
    round_number = 1
```

Avoid hidden defaults:

```python
def amend_spec(spec: Spec) -> Outcome:
    ...
    # somewhere later: stop after 5 rounds
```

---

## 14. Comments and Docstrings

**Source status:** **[Sourced / Adapted]** from PEP 257; **[Internal Convention]** for pseudocode.

PEP 257 recommends documenting behavior, arguments, return values, side effects, exceptions, and calling restrictions where applicable. This standard adapts that idea to pseudocode process blocks.

### 14.1 Process docstring

A complex process SHOULD include a short docstring.

```python
# PSEUDOCODE: Python-shaped process instruction, not executable Python.

def reduce_artifact_size(artifact: Artifact, limit: ByteSize) -> Outcome:
    """
    Reduce an artifact until it is under `limit`.

    Side effects:
        May rewrite the artifact.
        Must not remove required sections.

    Returns:
        Accepted if artifact size is <= limit.
        Blocked if required content cannot fit under limit.
    """
    ...
```

### 14.2 Comments explain intent, not hidden behavior

Good:

```python
# Keep approved sections stable to reduce review churn.
document = revise_only_blocked_sections(document, review.blockers)
```

Bad:

```python
# Keep approved sections stable.
document = revise_document(document)
```

The first example encodes the requirement in the function name. The second hides the rule in a comment.

### 14.3 TODO comments

TODO comments are allowed only if they produce a blocker or explicit follow-up action.

Bad:

```python
# TODO: define release gate later
release()
```

Good:

```python
if release_gate is None:
    return SpecificationDefect(reason="release gate is undefined")
```

---

## 15. Variables and Assignment

**Source status:** **[Sourced / Adapted]** from Python assignment and published pseudocode conventions; **[Internal Convention]** for agent state requirements.

### 15.1 Assignment

Use Python-style `=` assignment.

```python
round_number = 1
blockers = []
review = reviewer.review(document)
```

Do not use the pseudocode assignment arrow `←` inside Pythonic pseudocode blocks unless quoting another pseudocode dialect.

### 15.2 Mutable state

State that changes over time MUST be assigned to a variable.

```python
document = revise_document(document, blockers)
round_number += 1
```

Avoid actions that imply mutation without stating it:

```python
revise_document(document, blockers)
```

The example above may be acceptable only if the action is explicitly defined as mutating `document` in place. This standard recommends returning updated state instead.

### 15.3 State initialization

Initialize important state near the top of the process.

```python
blockers: list[Blocker] = []
approved_sections: set[SectionId] = set()
round_history: list[ReviewResult] = []
```

### 15.4 Avoid hidden globals

Bad:

```python
def release_project() -> Outcome:
    if tests_pass:
        release()
```

Good:

```python
def release_project(test_result: TestResult) -> Outcome:
    if test_result.status == "passed":
        release()
        return Accepted()

    return Blocked(reason="tests failed", evidence=test_result.failures)
```

---

## 16. Boolean Conditions and Comparisons

**Source status:** **[Sourced / Adapted]** from Python syntax; **[Internal Convention]** for agent readability.

### 16.1 Use explicit predicates

Good:

```python
if review.has_blockers:
    ...
```

Acceptable:

```python
if review.blockers:
    ...
```

Risky:

```python
if review:
    ...
```

The last example does not say what property matters.

### 16.2 Use positive conditions where possible

Prefer:

```python
if review.approved:
    return Accepted()
```

Over:

```python
if not review.rejected:
    return Accepted()
```

Positive conditions reduce ambiguity.

### 16.3 Compare states explicitly

```python
if review.status == "approved":
    return Accepted()

if review.status == "rejected":
    ...
```

Avoid relying on implicit truthiness for state values:

```python
if review.status:
    ...
```

### 16.4 Complex boolean expressions

Complex expressions SHOULD be named.

Bad:

```python
if repo.is_public and change.touches_release and ci.passed and approval.granted:
    merge_pr()
```

Good:

```python
release_merge_allowed = (
    repo.is_public
    and change.touches_release
    and ci.status == "passed"
    and approval.status == "granted"
)

if release_merge_allowed:
    merge_pr()
```

---

## 17. Conditional Branching

**Source status:** **[Sourced / Adapted]** from Python `if / elif / else`; **[Internal Convention]** for completeness requirements.

Python uses `if`, `elif`, and `else` for conditional branching. This standard adopts that structure.

### 17.1 Basic branching

```python
if review.status == "approved":
    return Accepted(document=document)
elif review.status == "rejected":
    document = revise_document(document, review.blockers)
else:
    return Blocked(reason="unknown review status", status=review.status)
```

### 17.2 Every branch must do something observable

Each branch MUST:

- Return an outcome.
- Mutate named state.
- Call an explicit action.
- Continue or break a loop.
- Delegate to a named subroutine.

Bad:

```python
if review.status == "approved":
    pass
```

Good:

```python
if review.status == "approved":
    return Accepted(document=document)
```

### 17.3 Always include fallback behavior

If the condition set is intended to be exhaustive, include an `else` that catches impossible or invalid states.

```python
if gate == "approved":
    merge_pr()
elif gate == "rejected":
    return Rejected(reason="user rejected merge")
elif gate == "needs_changes":
    return Blocked(reason="merge gate requires changes")
else:
    return SpecificationDefect(reason="unknown gate value", gate=gate)
```

### 17.4 Use `match` sparingly

Python supports `match`, but this standard recommends `if / elif / else` or a decision table for most agent pseudocode. Many agents and humans read simple `if` chains more reliably than structural pattern matching.

`match` MAY be used when the team explicitly adopts it.

---

## 18. Guard Clauses

**Source status:** **[Internal Convention]**, influenced by readability practice.

Guard clauses are early exits that handle invalid or exceptional conditions before the main path.

### 18.1 Required inputs

```python
if spec is None:
    return Blocked(reason="missing spec")

if plan is None:
    return Blocked(reason="missing plan")
```

### 18.2 Preconditions

```python
if not repo.exists:
    return Blocked(reason="repository does not exist", repo=repo.name)

if not repo.is_clean:
    return Blocked(reason="repository has uncommitted changes")
```

### 18.3 Main path after guards

```python
review = reviewer.review(plan)
```

Guard clauses keep the main path flat and readable.

### 18.4 Guard clause ordering

Recommended order:

1. Missing inputs.
2. Invalid inputs.
3. Unsafe state.
4. Permission or approval gates.
5. Already-complete conditions.
6. Main process.

---

## 19. For Loops

**Source status:** **[Sourced / Adapted]** from Python `for`; **[Internal Convention]** for bounded workflow semantics.

Use `for` when the number of iterations is known, bounded, or tied to a finite collection.

### 19.1 Bounded attempt loops

For retry-style loops, prefer `for attempt in range(...)`.

```python
for attempt in range(1, max_attempts + 1):
    result = try_generate_artifact()

    if result.success:
        return Accepted(artifact=result.artifact)

return Blocked(reason="max attempts reached")
```

This is clearer than a `while` loop because the cap is visible in the loop header.

### 19.2 Iterating over collections

```python
for file in changed_files:
    validation = validate_file(file)

    if validation.failed:
        blockers.append(validation.blocker)
```

### 19.3 Do not mutate a collection ambiguously while iterating

Bad:

```python
for blocker in blockers:
    if blocker.resolved:
        blockers.remove(blocker)
```

Good:

```python
unresolved_blockers = []

for blocker in blockers:
    if not blocker.resolved:
        unresolved_blockers.append(blocker)

blockers = unresolved_blockers
```

### 19.4 Use `enumerate` for positions

```python
for index, section in enumerate(sections, start=1):
    validate_section(index=index, section=section)
```

### 19.5 Loop result aggregation

When a loop gathers results, name the aggregate.

```python
validation_results = []

for file in changed_files:
    validation_results.append(validate_file(file))

if any(result.failed for result in validation_results):
    return Blocked(reason="validation failed", evidence=validation_results)
```

---

## 20. While Loops

**Source status:** **[Sourced / Adapted]** from Python `while`; **[Internal Convention]** for mandatory bounds.

Use `while` only when the number of iterations is not naturally known in advance.

### 20.1 Mandatory stop condition

Every `while` loop MUST include at least one explicit stop mechanism:

- A counter.
- A timeout.
- A max size delta.
- A max no-progress count.
- A state transition that reaches a terminal outcome.

Bad:

```python
while not approved:
    document = revise_document(document)
```

Good:

```python
round_number = 1

while not approved and round_number <= max_rounds:
    review = reviewer.review(document)

    if review.approved:
        approved = True
        break

    document = revise_document(document, review.blockers)
    round_number += 1

if not approved:
    return Blocked(reason="round cap reached")
```

Better when the cap is primary:

```python
for round_number in range(1, max_rounds + 1):
    review = reviewer.review(document)
    ...
```

### 20.2 While loop checklist

A `while` loop is valid only if it answers:

- What condition keeps the loop running?
- Which variable changes that condition?
- Where is that variable updated?
- What happens on success?
- What happens on cap/timeout/no-progress?
- What state is preserved after the loop?

### 20.3 Progress requirement

Every `while` loop MUST make progress toward termination.

Bad:

```python
while artifact.size > limit:
    summarize_artifact(artifact)
```

Good:

```python
previous_size = artifact.size
artifact = summarize_artifact(artifact)

if artifact.size >= previous_size:
    no_progress_count += 1
```

### 20.4 No-progress handling

For loops that optimize, reduce, search, or converge, define no-progress behavior.

```python
no_progress_count = 0

while artifact.size > limit and no_progress_count < max_no_progress_rounds:
    previous_size = artifact.size
    artifact = reduce_lowest_priority_content(artifact)

    if artifact.size >= previous_size:
        no_progress_count += 1
    else:
        no_progress_count = 0

if artifact.size > limit:
    return Blocked(reason="unable to reduce artifact below limit", size=artifact.size)
```

### 20.5 Avoid `while True`

`while True` is prohibited unless:

- The loop has explicit `break` or `return` paths.
- The loop has a visible cap or timeout.
- The reason for using `while True` is explained.

Acceptable:

```python
attempt = 1

while True:
    if attempt > max_attempts:
        return Blocked(reason="max attempts reached")

    result = try_action()

    if result.success:
        return Accepted(result=result)

    attempt += 1
```

Preferred:

```python
for attempt in range(1, max_attempts + 1):
    result = try_action()

    if result.success:
        return Accepted(result=result)

return Blocked(reason="max attempts reached")
```

---

## 21. Retry Loops

**Source status:** **[Internal Convention]**.

Retry loops are common in agent workflows. This standard defines a reliable pattern.

### 21.1 Standard retry pattern

```python
# PSEUDOCODE: Python-shaped process instruction, not executable Python.

def retry_until_valid(task: Task, max_attempts: int = 3) -> Outcome:
    last_error: Error | None = None

    for attempt in range(1, max_attempts + 1):
        result = run_task(task)

        if result.valid:
            return Accepted(result=result, attempts=attempt)

        last_error = result.error
        task = revise_task(task, result.error)

    return Blocked(
        reason="max attempts reached",
        attempts=max_attempts,
        last_error=last_error,
    )
```

### 21.2 Retry loop requirements

Every retry loop MUST define:

- `max_attempts` or equivalent cap.
- Attempt counter.
- Success condition.
- Retry condition.
- State update between attempts.
- Failure result after final attempt.
- Evidence to return when blocked.

### 21.3 Retry versus review loop

A retry loop repeats an action until it succeeds. A review loop alternates author and reviewer actions. Use different variable names.

Retry loop:

```python
for attempt in range(1, max_attempts + 1):
    result = generate_output()
```

Review loop:

```python
for round_number in range(1, max_review_rounds + 1):
    review = reviewer.review(document)
```

### 21.4 Backoff and waiting

For human-authored agent specs, avoid low-level timing unless required.

Acceptable:

```python
wait(backoff_policy.next_delay(attempt))
```

Better for most agent workflows:

```python
return Blocked(reason="external service unavailable; retry later")
```

Use real automation code for actual timed backoff.

---

## 22. Break, Continue, and Return

**Source status:** **[Sourced / Adapted]** from Python loop control; **[Internal Convention]** for usage limits.

### 22.1 Return

Use `return` for terminal outcomes.

```python
if review.approved:
    return Accepted(document=document)
```

`return` exits the current process immediately.

### 22.2 Continue

Use `continue` when the current iteration is complete and the next iteration should begin.

```python
if blocker.resolved:
    continue

unresolved_blockers.append(blocker)
```

### 22.3 Break

Use `break` when the loop should stop but the process must perform follow-up logic outside the loop.

```python
for candidate in candidates:
    if candidate.is_acceptable:
        selected = candidate
        break

if selected is None:
    return Blocked(reason="no acceptable candidate")
```

### 22.4 Prefer return over flag-plus-break for terminal success

Bad:

```python
accepted = False

for round_number in range(1, max_rounds + 1):
    if review.approved:
        accepted = True
        break

if accepted:
    return Accepted()
```

Good:

```python
for round_number in range(1, max_rounds + 1):
    if review.approved:
        return Accepted()
```

Use flags only when post-loop cleanup is required.

---

## 23. Error Handling and Blockers

**Source status:** **[Sourced / Adapted]** from Python exception concepts; **[Internal Convention]** for agent workflow outcomes.

Python has exceptions for runtime errors. Agent pseudocode usually needs workflow blockers instead.

### 23.1 Use `Blocked` for expected problems

Use `Blocked(...)` when the agent cannot safely continue.

```python
if tests.failed:
    return Blocked(reason="tests failed", failures=tests.failures)
```

### 23.2 Use `NeedsUserDecision` for choice points

```python
if merge_requires_user_approval:
    return NeedsUserDecision(
        question="Approve merge of release PR?",
        options=["approve", "reject", "revise"],
        default="reject",
    )
```

### 23.3 Use `SpecificationDefect` for bad instructions

```python
if max_rounds is None:
    return SpecificationDefect(reason="max_rounds is required but undefined")
```

### 23.4 Avoid silent failure

Bad:

```python
try_run_tests()
commit_changes()
```

Good:

```python
test_result = run_tests()

if test_result.failed:
    return Blocked(reason="tests failed", evidence=test_result.failures)

commit_changes()
```

### 23.5 Exceptions in pseudocode

Use `raise` only when describing implementation logic or unrecoverable specification defects.

```python
raise SpecificationDefect("release policy has no default branch rule")
```

For agent workflows, prefer returning structured outcomes.

---

## 24. Action Calls and Side Effects

**Source status:** **[Internal Convention]**.

A function call in Pythonic pseudocode usually means “the agent must perform this action.”

### 24.1 Required action semantics

The following call:

```python
run_tests()
```

means:

- The agent must execute, simulate, or otherwise perform the named action according to available tools.
- The agent must capture the result if later logic depends on it.
- The agent must not pretend the action succeeded without evidence when evidence is required.

### 24.2 Capture side-effect results

Bad:

```python
run_tests()
commit_changes()
```

Good:

```python
test_result = run_tests()

if test_result.status != "passed":
    return Blocked(reason="tests failed", evidence=test_result)

commit_changes()
```

### 24.3 Mark side effects in action names

Names SHOULD imply side effects.

| Side effect | Preferred verb |
|---|---|
| Writes a file | `write_*`, `update_*`, `rewrite_*` |
| Deletes content | `delete_*`, `remove_*` |
| Creates external item | `create_*`, `open_*` |
| Sends communication | `send_*`, `notify_*` |
| Reads information | `read_*`, `fetch_*`, `query_*` |
| Checks condition | `validate_*`, `verify_*`, `check_*` |

Example:

```python
plan = write_plan(spec)
review = review_plan(plan)
commit = create_commit(files=[plan.path])
```

### 24.4 Idempotency

If an action may be repeated, define whether it is idempotent.

```python
if not github_issue_exists(upstream_bug):
    issue = create_github_issue(upstream_bug)
else:
    issue = link_existing_github_issue(upstream_bug)
```

Do not write retry loops that create duplicate external records unless duplication is acceptable and explicitly handled.

---

## 25. User Interaction and Approval Gates

**Source status:** **[Internal Convention]**.

User approval gates are common in agent workflows. A gate must be explicit and inline with the agent conversation, not hidden in an external manual step unless the process intentionally requires that.

### 25.1 User decision outcome

```python
return NeedsUserDecision(
    question="Approve merge of release PR #42?",
    options=["approve", "reject", "request_changes"],
    default="reject",
    evidence=[ci_result, review_summary, risk_summary],
)
```

### 25.2 Approval is data

Treat user approval as a value assigned to a variable.

```python
approval = ask_user_for_approval(
    question="Merge release PR after CI passes?",
    evidence=[ci_result, review_result],
)

if approval.status == "approved":
    merge_pr()
    return Accepted(reason="user approved merge")

if approval.status == "rejected":
    return Rejected(reason="user rejected merge")

return Blocked(reason="ambiguous user approval response", approval=approval)
```

### 25.3 Never infer approval from silence

Silence, ambiguity, or tool failure MUST NOT be treated as approval.

```python
if approval.status != "approved":
    return Blocked(reason="approval not granted", approval=approval)
```

### 25.4 External manual action

If a workflow requires the user to perform an external manual action, the pseudocode MUST say so explicitly.

```python
return NeedsUserDecision(
    question="Manual GitHub repository setting change required. Proceed after completing it?",
    required_manual_action="Enable branch protection setting X in GitHub UI",
)
```

For automation-first workflows, prefer agent-mediated gates over manual external actions.

---

## 26. External Systems and Tool Use

**Source status:** **[Internal Convention]**.

When pseudocode references external systems, specify what is read, what is written, and how evidence is captured.

### 26.1 External read

```python
repo_settings = github.read_repository_settings(repo)

if repo_settings.branch_protection.missing_required_checks:
    return Blocked(
        reason="branch protection missing required checks",
        evidence=repo_settings.branch_protection,
    )
```

### 26.2 External write

```python
issue = github.create_issue(
    repo=upstream_repo,
    title=bug_report.title,
    body=bug_report.body,
)

if issue.url is None:
    return Blocked(reason="issue creation did not return URL", evidence=issue)
```

### 26.3 External write confirmation

After important external writes, verify the expected state.

```python
created_issue = github.create_issue(...)
verified_issue = github.read_issue(created_issue.id)

if verified_issue.status != "open":
    return Blocked(reason="created issue is not open", evidence=verified_issue)
```

### 26.4 Tool failure

```python
tool_result = run_tool(command)

if tool_result.status == "tool_unavailable":
    return Blocked(reason="required tool unavailable", tool=command.name)

if tool_result.status == "failed":
    return Blocked(reason="tool failed", stderr=tool_result.stderr)
```

---

## 27. Preconditions, Postconditions, and Invariants

**Source status:** **[Internal Convention]**, with concepts common in software specification.

### 27.1 Preconditions

Preconditions are requirements that must be true before the process starts.

```python
if not repo.exists:
    return Blocked(reason="repo does not exist")

if not spec.is_final:
    return Blocked(reason="spec must be final before planning")
```

### 27.2 Postconditions

Postconditions are requirements that must be true when the process returns success.

```python
if not tests_passed:
    return Blocked(reason="postcondition failed: tests must pass")

return Accepted(reason="implementation complete")
```

### 27.3 Invariants

Invariants must remain true throughout the process.

```md
## Invariants

- The agent MUST NOT exceed `max_rounds`.
- The agent MUST NOT discard unresolved blockers.
- The agent MUST NOT merge without explicit approval when `requires_user_approval == True`.
```

### 27.4 Encode invariants in pseudocode when possible

Bad:

```md
The agent must not exceed max rounds.
```

Better:

```python
for round_number in range(1, max_rounds + 1):
    ...

return Blocked(reason="round cap reached")
```

Use both when the invariant is important.

---

## 28. Decision Tables

**Source status:** **[Sourced / Adapted]** from decision-table practice and DMN; **[Internal Convention]** for Markdown form.

Use decision tables when branching has many combinations. A table is often more deterministic than nested `if` statements.

### 28.1 When to use a decision table

Use a decision table when:

- More than five branches exist.
- Multiple independent conditions combine.
- The logic is policy-like.
- Reviewers need to check completeness.
- The same decision appears in multiple processes.

### 28.2 Basic decision table

| Condition | Required action | Outcome |
|---|---|---|
| Missing required input | Ask user for input | `NeedsUserDecision` |
| Tests failed | Stop and report failures | `Blocked` |
| Tests passed and approval required | Ask user for approval | `NeedsUserDecision` |
| Tests passed and approval not required | Proceed | Continue |

### 28.3 Referencing a decision table from pseudocode

```python
decision = lookup_decision(
    table="merge_gate_decision_table",
    facts={
        "tests_status": tests.status,
        "approval_required": change.requires_user_approval,
        "approval_status": approval.status,
    },
)

if decision.outcome == "NeedsUserDecision":
    return NeedsUserDecision(question=decision.question, evidence=decision.evidence)

if decision.outcome == "Blocked":
    return Blocked(reason=decision.reason, evidence=decision.evidence)

if decision.action == "proceed":
    merge_pr()
    return Accepted(reason="merge completed")
```

### 28.4 Decision table completeness

A decision table SHOULD include either:

- A row for every possible combination, or
- A default row for unmatched cases.

Example default row:

| Condition | Required action | Outcome |
|---|---|---|
| No row matches | Stop and surface specification defect | `SpecificationDefect` |

---

## 29. State Transition Tables

**Source status:** **[Internal Convention]**, related to state-machine practice.

Use state transition tables when the process is best understood as states and transitions.

### 29.1 Basic state transition table

| Current state | Event / condition | Guard | Action | Next state |
|---|---|---|---|---|
| `DraftReady` | Review requested | `round <= max_rounds` | Reviewer reviews draft | `ReviewComplete` |
| `ReviewComplete` | Approved | — | Mark accepted | `Accepted` |
| `ReviewComplete` | Rejected | `round < max_rounds` | Revise and increment round | `DraftReady` |
| `ReviewComplete` | Rejected | `round == max_rounds` | Stop and surface blockers | `Blocked` |

### 29.2 State variable in pseudocode

```python
state = "DraftReady"
round_number = 1

while state not in ["Accepted", "Blocked"]:
    if state == "DraftReady":
        review = reviewer.review(document)
        state = "ReviewComplete"
        continue

    if state == "ReviewComplete" and review.approved:
        state = "Accepted"
        continue

    if state == "ReviewComplete" and round_number < max_rounds:
        document = revise_document(document, review.blockers)
        round_number += 1
        state = "DraftReady"
        continue

    state = "Blocked"
```

A state transition table is usually clearer than this pseudocode. Use both only when necessary.

### 29.3 Diagram generation

A Mermaid diagram MAY be generated from a state transition table. The table remains the source of truth unless the project explicitly says otherwise.

---

## 30. Combining Pseudocode, Tables, and Narrative

**Source status:** **[Internal Convention]**.

Use each representation for what it does best.

| Need | Best format |
|---|---|
| Main procedural flow | Pythonic pseudocode |
| Many condition combinations | Decision table |
| Lifecycle states | State transition table |
| Human intent | Short narrative |
| Acceptance examples | Given/When/Then |
| Requirements | MUST/SHOULD rules or EARS-style sentences |
| Visual overview | Mermaid or BPMN generated from the source table |

### 30.1 Recommended order

A complex process should be documented in this order:

1. Purpose.
2. Inputs and outputs.
3. High-level pseudocode.
4. Decision tables.
5. Invariants.
6. Acceptance examples.
7. Optional diagram.

### 30.2 Do not duplicate logic inconsistently

If pseudocode and a table disagree, the document must say which one wins.

Recommended rule:

```md
The pseudocode is the source of truth for sequence. Decision tables are the source of truth for branch selection. If they conflict, stop and surface a specification defect.
```

---

## 31. Conformance Levels

**Source status:** **[Internal Convention]**.

Projects MAY adopt one of three conformance levels.

### 31.1 Level 1: Lightweight

Use for quick instructions.

Requirements:

- Use Python-like indentation.
- Include explicit terminal outcomes.
- Include caps on loops.
- Avoid ambiguous `while True`.

### 31.2 Level 2: Standard

Use for project standards and agent workflow docs.

Requirements:

- All Level 1 requirements.
- Include the pseudocode sentinel comment.
- Define inputs and outputs.
- Use `Accepted`, `Blocked`, or equivalent outcomes.
- Include fallback behavior for unknown states.
- Include decision tables for broad branching.

### 31.3 Level 3: Strict

Use for critical workflows such as releases, merge gates, safety-critical automation, financial workflows, or destructive operations.

Requirements:

- All Level 2 requirements.
- Define preconditions, postconditions, and invariants.
- Define all side effects.
- Include user approval gates explicitly.
- Include a state transition table for stateful workflows.
- Include validation checks.
- Include worked examples for risky branches.
- Include `SpecificationDefect` behavior for contradictory instructions.

---

## 32. Validation and Lint Rules

**Source status:** **[Internal Convention]**.

These rules can be used manually or implemented by an agent as a pseudocode linter.

### 32.1 Structural rules

| Rule ID | Requirement |
|---|---|
| PSEUDO001 | Every non-trivial block MUST include the pseudocode sentinel. |
| PSEUDO002 | Every process MUST return a terminal outcome. |
| PSEUDO003 | Every `while` loop MUST have a cap, timeout, or explicit stop condition. |
| PSEUDO004 | Every retry loop MUST preserve last failure evidence. |
| PSEUDO005 | Every branch MUST perform an action, state update, loop control statement, or return. |
| PSEUDO006 | Every external write SHOULD be verified or its verification explicitly waived. |
| PSEUDO007 | Every user approval gate MUST define allowed responses. |
| PSEUDO008 | Every broad condition matrix SHOULD be represented as a decision table. |
| PSEUDO009 | Every terminal blocker SHOULD include reason and evidence. |
| PSEUDO010 | Comments MUST NOT contain the only copy of a requirement. |

### 32.2 Loop-specific lint checks

For each loop, check:

- Is the loop finite?
- Is the loop counter visible?
- Is the loop counter updated?
- Can success return?
- Can failure return?
- Is no-progress behavior defined when relevant?
- Is state preserved after failure?

### 32.3 Branch-specific lint checks

For each `if / elif / else` group, check:

- Are conditions mutually exclusive, or is ordering intentional?
- Is there a fallback `else`?
- Is unknown input handled?
- Are side effects visible?
- Does each path terminate or continue safely?

### 32.4 Outcome-specific lint checks

For every `Accepted(...)`:

- Are acceptance checks complete?
- Is evidence included where appropriate?
- Did required side effects occur before return?

For every `Blocked(...)`:

- Is the reason specific?
- Is evidence included?
- Is the next required decision or action clear?

For every `NeedsUserDecision(...)`:

- Is the question clear?
- Are options defined?
- Is the default safe?
- Is supporting evidence provided?

---

## 33. Anti-Patterns

**Source status:** **[Internal Convention]**.

### 33.1 Unbounded loop

Bad:

```python
while not approved:
    revise()
```

Correct:

```python
for round_number in range(1, max_rounds + 1):
    review = reviewer.review(document)

    if review.approved:
        return Accepted(document=document)

    document = revise_document(document, review.blockers)

return Blocked(reason="round cap reached")
```

### 33.2 Guess-and-check size reduction

Bad:

```python
while artifact.size > limit:
    shorten_artifact()
```

Correct:

```python
while artifact.size > limit and reduction_round <= max_reduction_rounds:
    required_reduction = artifact.size - limit
    reduction_plan = plan_reduction(artifact, required_reduction)
    artifact = apply_reduction_plan(artifact, reduction_plan)
    reduction_round += 1

if artifact.size > limit:
    return Blocked(reason="unable to reduce below limit", current_size=artifact.size, limit=limit)
```

### 33.3 Hidden side effects

Bad:

```python
prepare_release()
return Accepted()
```

Correct:

```python
changelog = update_changelog(release_notes)
version_file = update_version_file(version)
commit = create_commit(files=[changelog.path, version_file.path])
return Accepted(commit=commit)
```

### 33.4 Ambiguous approval

Bad:

```python
if user_says_ok:
    merge()
```

Correct:

```python
approval = ask_user_for_approval(options=["approve", "reject", "request_changes"])

if approval.status == "approve":
    merge_pr()
    return Accepted(reason="user approved merge")

if approval.status == "reject":
    return Rejected(reason="user rejected merge")

return Blocked(reason="user requested changes", requested_changes=approval.changes)
```

### 33.5 Comment-only requirement

Bad:

```python
# Stop after five tries.
while result.failed:
    result = retry()
```

Correct:

```python
for attempt in range(1, 5 + 1):
    result = retry()

    if result.success:
        return Accepted(result=result)

return Blocked(reason="five attempts failed", last_result=result)
```

### 33.6 Overly clever Python

Bad:

```python
return Accepted() if all(c.status == "ok" for c in checks) else Blocked()
```

Correct:

```python
failed_checks = []

for check in checks:
    if check.status != "ok":
        failed_checks.append(check)

if failed_checks:
    return Blocked(reason="checks failed", evidence=failed_checks)

return Accepted(reason="all checks passed")
```

Pseudocode should optimize for clear instruction, not clever compactness.

---

## 34. Worked Examples

**Source status:** **[Internal Convention]**.

### 34.1 Document review loop with round cap

```python
# PSEUDOCODE: Python-shaped process instruction, not executable Python.

def review_and_amend_document(
    document: MarkdownDocument,
    author: Agent,
    reviewer: Agent,
    max_rounds: int = 5,
) -> Outcome:
    unresolved_blockers: list[Blocker] = []
    review_history: list[ReviewResult] = []

    for round_number in range(1, max_rounds + 1):
        review = reviewer.review(document)
        review_history.append(review)

        if review.status == "approved":
            final_document = mark_document_final(document)
            return Accepted(
                document=final_document,
                rounds=round_number,
                review_history=review_history,
            )

        if review.status == "rejected" and review.blockers:
            unresolved_blockers = review.blockers
            document = author.revise_document(
                document=document,
                blockers=unresolved_blockers,
                preserve_accepted_sections=True,
            )
            continue

        return Blocked(
            reason="review returned ambiguous status",
            review=review,
            review_history=review_history,
        )

    return Blocked(
        reason="round cap reached",
        unresolved_blockers=unresolved_blockers,
        review_history=review_history,
    )
```

Key features:

- The loop is bounded.
- Approval returns immediately.
- Rejection carries blockers forward.
- Ambiguous review output is blocked.
- Final cap failure preserves history.

### 34.2 Artifact size reduction without random guessing

```python
# PSEUDOCODE: Python-shaped process instruction, not executable Python.

def reduce_artifact_to_limit(
    artifact: Artifact,
    size_limit: int,
    max_rounds: int = 3,
) -> Outcome:
    reduction_history: list[ReductionRound] = []

    for round_number in range(1, max_rounds + 1):
        current_size = measure_size(artifact)

        if current_size <= size_limit:
            return Accepted(
                artifact=artifact,
                final_size=current_size,
                reduction_history=reduction_history,
            )

        required_reduction = current_size - size_limit
        reduction_plan = plan_reduction(
            artifact=artifact,
            required_reduction=required_reduction,
            preserve_required_sections=True,
        )

        if not reduction_plan.can_meet_limit:
            return Blocked(
                reason="required content cannot fit within size limit",
                current_size=current_size,
                size_limit=size_limit,
                required_reduction=required_reduction,
                reduction_plan=reduction_plan,
            )

        artifact = apply_reduction_plan(artifact, reduction_plan)
        new_size = measure_size(artifact)

        reduction_history.append(
            ReductionRound(
                round_number=round_number,
                previous_size=current_size,
                new_size=new_size,
                required_reduction=required_reduction,
                plan=reduction_plan,
            )
        )

        if new_size >= current_size:
            return Blocked(
                reason="reduction made no progress",
                previous_size=current_size,
                new_size=new_size,
                reduction_history=reduction_history,
            )

    final_size = measure_size(artifact)

    if final_size <= size_limit:
        return Accepted(
            artifact=artifact,
            final_size=final_size,
            reduction_history=reduction_history,
        )

    return Blocked(
        reason="max reduction rounds reached",
        final_size=final_size,
        size_limit=size_limit,
        reduction_history=reduction_history,
    )
```

This avoids the inefficient pattern where an agent repeatedly edits, measures after the fact, and guesses again.

### 34.3 GitHub upstream bug reporting

```python
# PSEUDOCODE: Python-shaped process instruction, not executable Python.

def report_upstream_bug(
    downstream_repo: Repository,
    upstream_repo: Repository,
    bug: BugReport,
) -> Outcome:
    if bug.evidence is None:
        return Blocked(reason="bug report requires evidence")

    if upstream_repo is None:
        return Blocked(reason="upstream repository is unknown", bug=bug)

    existing_issue = github.find_matching_issue(
        repo=upstream_repo,
        bug_signature=bug.signature,
    )

    if existing_issue is not None:
        downstream_issue = github.create_issue(
            repo=downstream_repo,
            title=f"Track upstream bug: {bug.title}",
            body=link_to_existing_upstream_issue(bug, existing_issue),
        )
        return Accepted(
            reason="linked existing upstream issue",
            upstream_issue=existing_issue,
            downstream_issue=downstream_issue,
        )

    upstream_issue = github.create_issue(
        repo=upstream_repo,
        title=bug.title,
        body=format_bug_report(bug),
    )

    downstream_issue = github.create_issue(
        repo=downstream_repo,
        title=f"Track upstream bug: {bug.title}",
        body=link_to_new_upstream_issue(bug, upstream_issue),
    )

    return Accepted(
        reason="created upstream bug and downstream tracking issue",
        upstream_issue=upstream_issue,
        downstream_issue=downstream_issue,
    )
```

Key features:

- Avoids duplicate upstream issues when a matching issue already exists.
- Creates downstream traceability.
- Requires evidence before creating public issues.

### 34.4 Release approval gate

```python
# PSEUDOCODE: Python-shaped process instruction, not executable Python.

def merge_release_pr(
    repo: Repository,
    pull_request: PullRequest,
    ci_result: CIResult,
    review_result: ReviewResult,
) -> Outcome:
    if ci_result.status != "passed":
        return Blocked(reason="CI did not pass", evidence=ci_result)

    if review_result.status != "approved":
        return Blocked(reason="review not approved", evidence=review_result)

    approval = ask_user_for_approval(
        question=f"Approve merge of release PR {pull_request.number}?",
        options=["approve", "reject", "request_changes"],
        default="reject",
        evidence=[ci_result, review_result, summarize_release_risk(pull_request)],
    )

    if approval.status == "approve":
        merge_result = github.merge_pull_request(pull_request)
        return Accepted(reason="release PR merged", merge_result=merge_result)

    if approval.status == "reject":
        return Rejected(reason="user rejected release merge", approval=approval)

    if approval.status == "request_changes":
        return Blocked(reason="user requested changes", requested_changes=approval.changes)

    return Blocked(reason="ambiguous approval response", approval=approval)
```

Key features:

- The user approval happens inline in the process.
- Silence is not approval.
- CI and review gates are verified before asking for approval.

### 34.5 Decision table plus pseudocode

Decision table:

| Tests | Review | User approval required? | User decision | Action | Outcome |
|---|---|---:|---|---|---|
| Failed | Any | Any | Any | Stop | `Blocked` |
| Passed | Rejected | Any | Any | Stop | `Blocked` |
| Passed | Approved | No | N/A | Merge | `Accepted` |
| Passed | Approved | Yes | Approve | Merge | `Accepted` |
| Passed | Approved | Yes | Reject | Stop | `Rejected` |
| Passed | Approved | Yes | Request changes | Stop | `Blocked` |
| Any other combination | Any | Any | Any | Stop | `SpecificationDefect` |

Pseudocode:

```python
# PSEUDOCODE: Python-shaped process instruction, not executable Python.

def apply_merge_decision(facts: MergeFacts) -> Outcome:
    decision = lookup_decision(table="merge_gate", facts=facts)

    if decision.outcome == "Blocked":
        return Blocked(reason=decision.reason, evidence=facts)

    if decision.outcome == "Rejected":
        return Rejected(reason=decision.reason, evidence=facts)

    if decision.outcome == "SpecificationDefect":
        return SpecificationDefect(reason="merge gate table did not match facts", facts=facts)

    if decision.action == "merge":
        merge_result = merge_pr(facts.pull_request)
        return Accepted(reason="merged", merge_result=merge_result)

    return SpecificationDefect(reason="unknown decision action", decision=decision)
```

---

## 35. Authoring Workflow

**Source status:** **[Internal Convention]**.

Use this workflow when writing complex pseudocode instructions.

### 35.1 Step 1: Write the narrative intent

One paragraph:

```md
The process reviews a document, allows bounded amendment rounds, commits the final artifact when approved, and stops with unresolved blockers if the round cap is reached.
```

### 35.2 Step 2: List state variables

```md
State:
- `document`
- `round_number`
- `review`
- `blockers`
- `review_history`
```

### 35.3 Step 3: List terminal outcomes

```md
Outcomes:
- `Accepted(document, review_history)`
- `Blocked(reason, unresolved_blockers, review_history)`
- `SpecificationDefect(reason)`
```

### 35.4 Step 4: Write the pseudocode

Write the main flow using `def`, guards, loops, and explicit outcomes.

### 35.5 Step 5: Extract broad branching into decision tables

If the pseudocode has too many `elif` branches, convert the branch logic into a table.

### 35.6 Step 6: Lint for failure modes

Check:

- Does every loop end?
- Does every branch return or act?
- Is every side effect visible?
- Does failure return evidence?
- Is user approval explicit?
- Is there ambiguity fallback?

### 35.7 Step 7: Add examples

Add at least one example for:

- Happy path.
- Rejected/retry path.
- Cap-reached path.
- Ambiguous input path.

---

## 36. Minimal Adoption Template

**Source status:** **[Internal Convention]**.

Copy this into a project standard if you need a compact version.

````md
# Pythonic Pseudocode Convention

Pythonic pseudocode in this repository is a structured process notation for humans and AI agents. It is not required to be executable Python.

Normative pseudocode blocks MUST begin with:

```python
# PSEUDOCODE: Python-shaped process instruction, not executable Python.
```

Rules:

- Use Python-like indentation, `def`, `if / elif / else`, `for`, `while`, and `return`.
- Use `snake_case` for variables/actions and `PascalCase` for outcomes/types.
- Every process MUST return an explicit terminal outcome such as `Accepted`, `Blocked`, `Rejected`, `Skipped`, or `NeedsUserDecision`.
- Every `while` loop MUST include a cap, timeout, or explicit stop condition.
- Retry loops SHOULD use `for attempt in range(1, max_attempts + 1)`.
- Every branch MUST perform an action, update state, continue/break a loop, or return an outcome.
- External writes MUST be explicit and SHOULD be verified.
- User approval MUST be explicit and MUST NOT be inferred from silence.
- Comments MAY explain intent but MUST NOT contain the only copy of a requirement.
- Broad condition matrices SHOULD be expressed as decision tables rather than deeply nested conditionals.
````

---

## 37. Reference Cheatsheet

**Source status:** **[Internal Convention]**.

### 37.1 Preferred control-flow patterns

| Need | Use |
|---|---|
| Bounded retry | `for attempt in range(1, max_attempts + 1)` |
| Review loop | `for round_number in range(1, max_rounds + 1)` |
| Unknown-length loop | `while condition and cap_not_reached` |
| Immediate success | `return Accepted(...)` |
| Missing input | `return Blocked(...)` or `NeedsUserDecision(...)` |
| User choice | `approval = ask_user_for_approval(...)` |
| Too many branches | Decision table |
| State lifecycle | State transition table |

### 37.2 Standard outcome constructors

```python
Accepted(reason: str, **evidence)
Blocked(reason: str, **evidence)
NeedsUserDecision(question: str, options: list[str], default: str, **evidence)
Rejected(reason: str, **evidence)
Skipped(reason: str, **evidence)
Superseded(reason: str, replacement: Artifact | None, **evidence)
SpecificationDefect(reason: str, **evidence)
```

These constructors are internal convention.

### 37.3 Standard review loop

```python
# PSEUDOCODE: Python-shaped process instruction, not executable Python.

def standard_review_loop(artifact: Artifact, max_rounds: int = 5) -> Outcome:
    blockers = []

    for round_number in range(1, max_rounds + 1):
        review = review_artifact(artifact)

        if review.approved:
            return Accepted(artifact=artifact, rounds=round_number)

        if review.blockers:
            blockers = review.blockers
            artifact = revise_artifact(artifact, blockers)
            continue

        return Blocked(reason="ambiguous review result", review=review)

    return Blocked(reason="round cap reached", unresolved_blockers=blockers)
```

### 37.4 Standard validation gate

```python
validation = validate_artifact(artifact)

if validation.failed:
    return Blocked(reason="validation failed", evidence=validation.failures)
```

### 37.5 Standard user approval gate

```python
approval = ask_user_for_approval(
    question="Approve this action?",
    options=["approve", "reject", "request_changes"],
    default="reject",
    evidence=evidence,
)

if approval.status == "approve":
    perform_action()
    return Accepted(reason="approved action completed")

if approval.status == "reject":
    return Rejected(reason="user rejected action")

return Blocked(reason="user requested changes or response was ambiguous", approval=approval)
```

---

## 38. Glossary

**Source status:** **[Internal Convention]** unless noted.

| Term | Meaning |
|---|---|
| Agent | An AI or automation actor expected to follow the instruction. |
| Artifact | A file, document, plan, spec, commit, PR, issue, or other output. |
| Blocker | A condition that prevents safe continuation. |
| Branch | A conditional path selected by `if`, `elif`, `else`, or a decision table. |
| Cap | A hard maximum number of attempts, rounds, or iterations. |
| Decision table | A table mapping facts or conditions to required actions/outcomes. |
| Guard clause | An early branch that exits on invalid, unsafe, missing, or already-complete conditions. |
| Invariant | A condition that must remain true throughout the process. |
| Outcome | A terminal return value such as `Accepted` or `Blocked`. |
| Postcondition | A condition that must be true after successful completion. |
| Precondition | A condition that must be true before the process starts. |
| Pseudocode | A structured, human-readable notation resembling code but not necessarily executable. |
| Review loop | A bounded cycle where an artifact is reviewed, amended, and reviewed again. |
| Retry loop | A bounded cycle that repeats an action until success or cap. |
| Side effect | A change outside local pseudocode state, such as writing files or opening a PR. |
| State transition table | A table mapping current state and event/guard to action and next state. |

---

## 39. Sources

### 39.1 Python language and style

1. Python Software Foundation. “Compound statements.” *Python Language Reference*.  
   <https://docs.python.org/3/reference/compound_stmts.html>  
   Used for the sourced foundation that Python compound statements include `if`, `while`, `for`, `try`, `with`, function definitions, clause headers, colons, and indented suites.

2. Python Software Foundation. “Lexical analysis: Indentation.” *Python Language Reference*.  
   <https://docs.python.org/3/reference/lexical_analysis.html>  
   Used for the sourced foundation that indentation determines grouping in Python.

3. van Rossum, Guido; Warsaw, Barry; Coghlan, Nick. “PEP 8 – Style Guide for Python Code.”  
   <https://peps.python.org/pep-0008/>  
   Used for naming, consistency, and readability guidance. This standard adapts PEP 8 conventions for pseudocode.

4. Goodger, David; van Rossum, Guido. “PEP 257 – Docstring Conventions.”  
   <https://peps.python.org/pep-0257/>  
   Used for the idea that behavior, arguments, return values, side effects, exceptions, and calling restrictions should be documented where applicable.

5. van Rossum, Guido; Lehtosalo, Jukka; Langa, Łukasz. “PEP 484 – Type Hints.”  
   <https://peps.python.org/pep-0484/>  
   Used for the sourced foundation of Python type-annotation syntax. This standard adapts annotations descriptively for pseudocode.

6. Python Software Foundation. “typing — Support for type hints.” *Python Standard Library*.  
   <https://docs.python.org/3/library/typing.html>  
   Used as a reference for type-hint vocabulary.

### 39.2 Normative language

7. Bradner, Scott. “RFC 2119: Key words for use in RFCs to Indicate Requirement Levels.” IETF, 1997.  
   <https://datatracker.ietf.org/doc/html/rfc2119>  
   Used for the sourced definitions of requirement keywords such as MUST, SHOULD, and MAY.

8. Leiba, Barry. “RFC 8174: Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words.” IETF, 2017.  
   <https://www.rfc-editor.org/rfc/rfc8174.html>  
   Used for the rule that BCP 14 keyword meanings apply when the terms are uppercase.

### 39.3 Published pseudocode dialects

9. College Board. “AP Computer Science Principles Exam Reference Information.”  
   <https://apcentral.collegeboard.org/media/pdf/ap-computer-science-principles-exam-reference-sheet.pdf>  
   Used as evidence of a published educational pseudocode dialect defining procedures, returns, list operations, and loops.

10. Cambridge International Education. “Cambridge International AS & A Level Computer Science 9618 Pseudocode Guide for Teachers for 2026.”  
    <https://www.cambridgeinternational.org/Images/697401-2026-pseudocode-guide-for-teachers.pdf>  
    Used as evidence of a published educational pseudocode dialect defining assignment, data types, selection, iteration, procedures, functions, and file handling.

### 39.4 Requirements, examples, and decision modeling

11. Mavin, Alistair. “EARS: Easy Approach to Requirements Syntax.”  
    <https://alistairmavin.com/ears/>  
    Used as an adjacent requirements-writing convention. This standard does not adopt EARS wholesale.

12. Cucumber. “Gherkin Reference.”  
    <https://cucumber.io/docs/gherkin/reference/>  
    Used as an adjacent convention for Given/When/Then behavioral examples.

13. Object Management Group. “Decision Model and Notation (DMN).”  
    <https://www.omg.org/dmn/>  
    Used as an adjacent source for the value of decision modeling and decision tables.

14. Object Management Group. “Business Process Model and Notation (BPMN), Version 2.0.2.”  
    <https://www.omg.org/spec/BPMN/2.0.2/About-BPMN>  
    Used as an adjacent source for formal process notation context. This standard does not require BPMN.

### 39.5 Internal convention disclosure

The following parts of this standard are intentionally internal convention rather than externally published standards:

- The required pseudocode sentinel comment.
- The exact outcome vocabulary: `Accepted`, `Blocked`, `NeedsUserDecision`, `Rejected`, `Skipped`, `Superseded`, and `SpecificationDefect`.
- The rule that agent workflow failures should usually return structured outcomes instead of raising exceptions.
- The use of actor-qualified calls such as `claude.review_plan(...)` or `github.create_issue(...)` as agent-action notation.
- The pseudocode lint rule IDs.
- The conformance levels.
- The exact templates and worked examples.
- The rule that decision tables are preferred when branching exceeds five cases.
- The rule that the table is the source of truth for broad branch selection while pseudocode is the source of truth for sequence.

---

## Closing Recommendation

Use this standard as the baseline for AI-agent process instructions when ordinary prose is too ambiguous and formal diagram syntax is too expensive. The strongest default pattern is:

```md
Purpose + Inputs + Outputs + Pythonic pseudocode + Decision tables + Invariants + Stop conditions + Examples
```

For your use case, the most important rules are:

1. Use Python-shaped pseudocode because Python control flow matches your mental model.
2. Make every loop bounded.
3. Make every branch observable.
4. Return structured outcomes.
5. Use decision tables when branch logic gets wide.
6. Treat diagrams as generated views, not the primary source of truth.
