---
schema_version: '1.1'
id: 'reference-syjjuy-apseudo-rule-catalog'
title: 'APSEUDO Rule Catalog'
description: 'Reference catalog for APSEUDO validation rules.'
doc_type: 'reference'
status: 'active'
created: '2026-07-09'
updated: '2026-07-09'
reviewed: null
owner: 'language-maintainers'
consumer: 'mix'
tags:
  - 'reference'
  - 'language'
  - 'rules'
  - 'validator'
aliases:
  - 'APSEUDO rules'
  - 'Rule catalog'
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# APSEUDO Rule Catalog

This file is generated from `src/apseudo_lint/rules.py`. It is the shared explanatory layer for the CLI, language server, MCP server, hooks, and documentation.

## APSEUDO-ACTION-001: Mutating action should be followed by verification

- **Default severity:** warning
- **Source:** Internal convention

Mutating actions should be followed by verify/check/test/review or a terminal outcome.

**Rationale:** Agent workflows should not silently assume that a change succeeded.

**Non-compliant:**

```text
write_file(path, content)
return Accepted()
```

**Compliant:**

```text
write_file(path, content)
verify_file(path)
return Accepted()
```

**Fix:** Add a verification action or @no_verification_required with rationale.

## APSEUDO-ACTION-002: Action names should use lower_snake_case

- **Default severity:** warning
- **Source:** Internal convention

Agent action/function calls should use lower_snake_case unless they are outcome constructors.

**Rationale:** Consistent action names improve completions, search, and rename behavior.

**Non-compliant:**

```text
ReviewDocument(document)
```

**Compliant:**

```text
review_document(document)
```

**Fix:** Rename the action to lower_snake_case.

## APSEUDO-BRANCH-001: if/elif chain should have fallback

- **Default severity:** warning
- **Source:** Internal convention

Non-terminal if/elif chains should include else or be annotated @exhaustive.

**Rationale:** Fallback branches prevent silent no-op behavior when a condition is unexpected.

**Non-compliant:**

```text
if approved:
    return Accepted()
```

**Compliant:**

```text
if approved:
    return Accepted()
else:
    return Blocked(reason="not approved")
```

**Fix:** Add else with an explicit action/outcome, or annotate @exhaustive when the condition set is complete.

## APSEUDO-BRANCH-002: Placeholder body should be resolved

- **Default severity:** warning
- **Source:** Internal convention

A branch body containing only pass or ... is considered incomplete.

**Rationale:** Placeholders are easy for agents to skip accidentally.

**Non-compliant:**

```text
else:
    pass
```

**Compliant:**

```text
else:
    return Blocked(reason="unsupported state")
```

**Fix:** Replace the placeholder or mark the branch with @allow_empty_branch.

## APSEUDO-FOR-001: For loop iterable should be visibly bounded

- **Default severity:** warning
- **Source:** Internal convention

for loops should iterate over a named collection, literal collection, range, or annotated bounded source.

**Rationale:** Unclear generator/call expressions can hide unbounded or side-effectful work.

**Non-compliant:**

```text
for item in fetch_items():
    process_item(item)
```

**Compliant:**

```text
items = fetch_items(limit=max_items)
for item in items:
    process_item(item)
```

**Fix:** Name the collection, use range/literal data, or add @bounded/@finite_collection.

## APSEUDO-IO-001: File must be valid UTF-8

- **Default severity:** error
- **Source:** Internal convention

Supported pseudocode and Markdown files must be readable as UTF-8.

**Rationale:** Agent-facing standards should be portable across local editors, CI, and remote agents.

**Non-compliant:**

```text
<non UTF-8 bytes>
```

**Compliant:**

```text
# UTF-8 encoded pseudocode
process demo():
    return Accepted()
```

**Fix:** Re-save the file as UTF-8.

## APSEUDO-IO-002: Input path must exist

- **Default severity:** error
- **Source:** Internal convention

Explicit files passed to the linter must exist.

**Rationale:** Missing files usually indicate a broken hook, stale CI path, or mistyped command.

**Non-compliant:**

```text
apseudo-lint docs/missing.apseudo
```

**Compliant:**

```text
apseudo-lint docs/process.apseudo
```

**Fix:** Correct the path or remove the stale reference.

## APSEUDO-NEST-001: Nesting should stay shallow

- **Default severity:** warning
- **Source:** Internal convention

Nesting deeper than the configured maximum should be refactored.

**Rationale:** Deeply nested agent instructions are harder for humans and models to follow reliably.

**Non-compliant:**

```text
if a:
    if b:
        if c:
            if d:
                if e:
                    return Accepted()
```

**Compliant:**

```text
if not a:
    return Blocked(reason="a missing")
if not b:
    return Blocked(reason="b missing")
return Accepted()
```

**Fix:** Use guard clauses, helper processes, or decision tables.

## APSEUDO-NORM-001: Normative keywords must be uppercase

- **Default severity:** warning
- **Source:** RFC 2119-inspired internal convention

Use uppercase RFC-style normative terms: MUST, MUST NOT, SHOULD, SHOULD NOT, MAY, REQUIRED, OPTIONAL.

**Rationale:** Uppercase normative keywords make hard requirements visually distinct from ordinary prose.

**Non-compliant:**

```text
# agent should run tests
```

**Compliant:**

```text
# agent SHOULD run tests
```

**Fix:** Run apseudo-format or uppercase the normative term manually.

## APSEUDO-NORM-002: Use MUST/SHOULD/MAY instead of SHALL

- **Default severity:** warning
- **Source:** Internal convention

The standard avoids SHALL and SHALL NOT to keep the vocabulary small.

**Rationale:** Agents and reviewers get more consistent signal from one compact normative vocabulary.

**Non-compliant:**

```text
# agent SHALL stop on blockers
```

**Compliant:**

```text
# agent MUST stop on blockers
```

**Fix:** Replace SHALL with MUST, and SHALL NOT with MUST NOT.

## APSEUDO-OUTCOME-001: Returned outcome must be approved

- **Default severity:** warning
- **Source:** Internal convention

Returned outcome names must appear in the configured allowed outcome set.

**Rationale:** A finite outcome vocabulary lets agents, hooks, and reports classify process endings consistently.

**Non-compliant:**

```text
return Done()
```

**Compliant:**

```text
return Accepted(reason="done")
```

**Fix:** Use an approved outcome or add the intentional project-specific outcome to .apseudo-lint.toml.

## APSEUDO-PARSE-001: Block header must use the standard shape

- **Default severity:** error
- **Source:** Python compound-statement-inspired internal convention

Process, branch, loop, and exception headers must follow their Pythonic pseudocode forms and end with a colon.

**Rationale:** The validator and agents rely on Python-shaped block headers to identify structure.

**Non-compliant:**

```text
if approved
    return Accepted()
```

**Compliant:**

```text
if approved:
    return Accepted()
```

**Fix:** Add the missing colon or rewrite the header using the documented block form.

## APSEUDO-PARSE-002: Block header must have an indented body

- **Default severity:** error
- **Source:** Internal convention

Every block header must be followed by at least one indented executable line unless explicitly allowed.

**Rationale:** Empty branches are ambiguous instructions for agents.

**Non-compliant:**

```text
if approved:
return Accepted()
```

**Compliant:**

```text
if approved:
    return Accepted()
```

**Fix:** Indent the body, add a real action, or annotate an intentionally empty branch with @allow_empty_branch.

## APSEUDO-PROC-001: Full workflow block should declare a process

- **Default severity:** warning
- **Source:** Internal convention

Standalone workflow snippets should start with process name(...): or def name(...): unless configured otherwise.

**Rationale:** Named processes are addressable by agents, language-server symbols, templates, and generated diagrams.

**Non-compliant:**

```text
review = review_document(document)
return Accepted()
```

**Compliant:**

```text
process review_document_flow(document):
    review = review_document(document)
    return Accepted()
```

**Fix:** Wrap the snippet in a process declaration or add @allow_missing_process for a fragment.

## APSEUDO-RETURN-001: Process must have a terminal return outcome

- **Default severity:** error
- **Source:** Internal convention

Every process must return at least one approved outcome.

**Rationale:** Agents need explicit success/failure outcomes to know when the workflow is complete.

**Non-compliant:**

```text
process demo():
    do_work()
```

**Compliant:**

```text
process demo():
    do_work()
    return Accepted(reason="done")
```

**Fix:** Add a terminal return such as Accepted(...), Blocked(...), or NeedsUserDecision(...).

## APSEUDO-RETURN-002: Return must use an outcome value

- **Default severity:** warning
- **Source:** Internal convention

Bare return statements and arbitrary return values are discouraged.

**Rationale:** Outcome constructors make termination states explicit and searchable.

**Non-compliant:**

```text
return
```

**Compliant:**

```text
return Blocked(reason="missing required input")
```

**Fix:** Return an approved outcome constructor or add a project outcome to the config.

## APSEUDO-RETURN-003: Process should end with an explicit terminal statement

- **Default severity:** warning
- **Source:** Internal convention

The final executable line in a process should be return, raise, break, or continue.

**Rationale:** A non-terminal trailing action can make completion ambiguous.

**Non-compliant:**

```text
process demo():
    do_work()
    verify_work()
```

**Compliant:**

```text
process demo():
    do_work()
    verify_work()
    return Accepted(reason="verified")
```

**Fix:** Append an explicit return outcome or justify the non-return terminal action.

## APSEUDO-WHILE-001: While loop must have a bounded stop condition

- **Default severity:** error
- **Source:** Internal convention

while loops must include a cap, timeout, deadline, maximum counter, or explicit bounded annotation.

**Rationale:** Unbounded loops are one of the highest-risk failure modes for autonomous agents.

**Non-compliant:**

```text
while not approved:
    revise(document)
```

**Compliant:**

```text
while not approved and round <= max_rounds:
    revise(document)
    round += 1
```

**Fix:** Add a bounded condition, update loop state, or annotate a genuine external stop condition.

## APSEUDO-WHILE-002: While body should update loop-control state

- **Default severity:** warning
- **Source:** Internal convention

A while loop should visibly mutate state used by the condition or terminate from inside the loop.

**Rationale:** A bounded-looking loop can still be infinite if its condition never changes.

**Non-compliant:**

```text
while round <= max_rounds:
    revise(document)
```

**Compliant:**

```text
while round <= max_rounds:
    revise(document)
    round += 1
```

**Fix:** Update the condition variable, return/break from the loop, or annotate an external stop condition.

## APSEUDO-WHILE-003: while True must visibly terminate

- **Default severity:** error
- **Source:** Internal convention

while True requires an explicit annotation and a visible break, return, or raise in the loop body.

**Rationale:** Intentional infinite loops are exceptional and must document their exit path.

**Non-compliant:**

```text
while True:
    poll_queue()
```

**Compliant:**

```text
# @intentional_infinite_loop until shutdown_requested
while True:
    if shutdown_requested:
        return Accepted(reason="shutdown")
```

**Fix:** Prefer a bounded while condition; otherwise annotate and add a reachable terminal statement.
