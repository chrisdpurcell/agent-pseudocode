---
schema_version: '1.1'
id: 'research-xai2pj-explaining-processes-to-ai'
title: 'Explaining Processes to AI'
description: 'Historical source conversation about explaining processes to AI agents.'
doc_type: 'research'
status: 'archived'
created: '2026-07-08'
updated: '2026-07-09'
reviewed: null
owner: 'language-maintainers'
consumer: 'mix'
tags:
  - 'research'
  - 'agent-workflow'
aliases: []
related: []
source:
  - 'https://chatgpt.com/c/6a4eb43a-2924-83ea-9262-6deed8788054'
confidence: 'medium'
visibility: 'internal'
license: null
---

# Explaining Processes to AI

<!-- prettier-ignore-start -->

**You:**

I’m interested in learning how to explain processes to an AI agent using shorthand like pseudo code versus longform narrative instruction. What options are available that are commonly used and and well regarded as effective.  I know something like mermaid diagram code is good at being deterministic, but that requires knowing mermaid is there a convention or language which offers a level of determinism without necessarily having to require perfect use of syntax?

* * *

**ChatGPT:**

I’ll frame this as a practical taxonomy: from loose prose to strict DSLs, then recommend the “sweet spot” formats that work well with coding agents without requiring perfect diagram syntax.

One early conclusion: the “determinism” you want usually comes less from a diagram language and more from explicit states, guards, stop conditions, and acceptance checks. Mermaid is just one rendering of that logic.

The best answer is **controlled Markdown**: ordinary Markdown plus a small, consistent grammar for states, decisions, requirements, and examples. It gives you most of the determinism of Mermaid without making the agent depend on perfect Mermaid syntax.

There is **no single universal “Mermaid but syntax-forgiving” standard** for AI agents. The strongest practical pattern is to combine several mature conventions:

| Convention | Best use | Syntax burden | Good for agents? |
| --- | --- | --- | --- |
| **Structured pseudo-code** | Procedures, loops, retries, branching | Low | Excellent |
| **State transition tables** | Agent workflows, approval loops, failure paths | Low | Excellent |
| **Decision tables / DMN-style rules** | Branching logic, policy rules | Medium-low | Excellent |
| **Gherkin / Given-When-Then** | Acceptance criteria and behavioral examples | Low-medium | Very good |
| **EARS requirements** | Clear requirement sentences | Low | Very good |
| **RFC 2119 verbs** | Normative force: MUST, SHOULD, MAY | Very low | Excellent |
| **BPMN / Mermaid / PlantUML / DOT** | Rendered diagrams | Medium-high | Good, but syntax-sensitive |
| **SCXML / formal state machines / TLA+ / PDDL** | Executable or formally analyzable workflows | High | Usually overkill |

## Recommended convention: controlled Markdown process specs

For AI agents, I would use this as the default:

```Markdown
# Process: <name>

## Intent
One paragraph describing the outcome.

## Actors
- Author
- Reviewer
- Implementer

## Inputs
- <input document>
- <constraints>
- <prior state>

## Outputs
- <output artifact>
- <decision record>
- <open blockers, if any>

## State transition table

| ID | Current state | Event / condition | Guard | Action | Next state |
|---|---|---|---|---|---|
| T1 | DraftReady | Review requested | round < 5 | Reviewer reviews draft | ReviewComplete |
| T2 | ReviewComplete | Blockers found | round < 5 | Author revises; increment round | DraftReady |
| T3 | ReviewComplete | No blockers | — | Mark accepted | Accepted |
| T4 | ReviewComplete | Blockers found | round = 5 | Stop and surface unresolved blockers | Blocked |

## Rules
- R1: The agent MUST increment `round` once per completed review cycle.
- R2: The agent MUST NOT continue past `round = 5`.
- R3: The agent SHOULD preserve accepted sections unless a blocker explicitly references them.

## Stop conditions
- Accepted.
- Blocked after round cap.
- Missing required input.

## Acceptance checks
- Every loop has an exit.
- Every decision has an explicit fallback.
- Every output has an owner and location.
```

That format is forgiving because small punctuation mistakes do not destroy the meaning, but it is still deterministic because the process has named states, guards, transitions, rules, and stop conditions.

## The pieces worth borrowing

### 1. RFC 2119 verbs for rule strength

Use **MUST**, **MUST NOT**, **SHOULD**, **MAY**, and **OPTIONAL** deliberately. RFC 2119 defines these as requirement-level keywords; for example, **MUST** means an absolute requirement, **MUST NOT** means an absolute prohibition, and **SHOULD** allows exceptions only when the implications are understood. [![](https://www.google.com/s2/favicons?domain=https://datatracker.ietf.org&sz=128)IETF Datatracker](https://datatracker.ietf.org/doc/html/rfc2119)

For agent instructions, this is extremely useful:

```Markdown
- The agent MUST run tests before declaring implementation complete.
- The agent MUST NOT silently skip failing checks.
- The agent SHOULD prefer the existing project pattern over introducing a new abstraction.
- The agent MAY create a helper script if it reduces repeated manual steps.
```

This is better than “try to,” “make sure,” or “normally,” because the force of the instruction is explicit.

### 2. EARS for natural-language requirements

EARS is probably the closest thing to what you’re asking for: a **controlled natural language** that constrains normal English without requiring a programming-like syntax. It uses a small set of sentence patterns with clauses in a predictable order, such as “While <precondition>, when <trigger>, the <system> shall <response>.” [![](https://www.google.com/s2/favicons?domain=https://alistairmavin.com&sz=128)Alistair Mavin](https://alistairmavin.com/ears/)

For agents, I would adapt EARS like this:

```Markdown
When the implementation changes public behavior, the agent MUST update relevant tests.

While unresolved blockers exist, the agent MUST NOT mark the plan complete.

If the agent reaches the round cap with blockers still open, then the agent MUST stop and surface the blockers.
```

EARS is strongest for requirements. It is weaker for long multi-step workflows unless paired with a transition table.

### 3. Gherkin for examples and acceptance criteria

Gherkin uses keywords such as **Feature**, **Rule**, **Scenario**, **Given**, **When**, **Then**, **And**, and **But** to structure executable specifications. Cucumber’s reference describes those keywords as giving structure and meaning to executable specs. [![](https://www.google.com/s2/favicons?domain=https://cucumber.io&sz=128)Cucumber](https://cucumber.io/docs/gherkin/reference/)

For AI agents, you do not need fully executable Cucumber tests to benefit from the shape:

```gherkin
Scenario: Review loop stops at the round cap
  Given the review round is 5
  And blockers remain unresolved
  When the reviewer rejects the document
  Then the agent stops the loop
  And the agent surfaces the unresolved blockers
  And the agent does not attempt another revision round
```

Gherkin is excellent for **behavioral examples**. I would not use it as the main process language for complex workflows; it gets verbose.

### 4. State transition tables for workflows

For your use case, this is the highest-value format. A state table is basically Mermaid’s logic without Mermaid’s syntax.

Instead of:

Mermaid![](data:image/svg+xml;utf8,%3Csvg%20id%3D%22mermaid-_r_vt_%22%20width%3D%2286.87999725341797%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20class%3D%22flowchart%22%20height%3D%22183.760009765625%22%20viewBox%3D%220%200%2086.87999725341797%20183.760009765625%22%20role%3D%22graphics-document%20document%22%20aria-roledescription%3D%22flowchart-v2%22%3E%3Cstyle%3E%23mermaid-_r_vt_%7Bfont-family%3A%22trebuchet%20ms%22%2Cverdana%2Carial%2Csans-serif%3Bfont-size%3A16px%3Bfill%3A%23ccc%3B%7D%40keyframes%20edge-animation-frame%7Bfrom%7Bstroke-dashoffset%3A0%3B%7D%7D%40keyframes%20dash%7Bto%7Bstroke-dashoffset%3A0%3B%7D%7D%23mermaid-_r_vt_%20.edge-animation-slow%7Bstroke-dasharray%3A9%2C5!important%3Bstroke-dashoffset%3A900%3Banimation%3Adash%2050s%20linear%20infinite%3Bstroke-linecap%3Around%3B%7D%23mermaid-_r_vt_%20.edge-animation-fast%7Bstroke-dasharray%3A9%2C5!important%3Bstroke-dashoffset%3A900%3Banimation%3Adash%2020s%20linear%20infinite%3Bstroke-linecap%3Around%3B%7D%23mermaid-_r_vt_%20.error-icon%7Bfill%3A%23a44141%3B%7D%23mermaid-_r_vt_%20.error-text%7Bfill%3A%23ddd%3Bstroke%3A%23ddd%3B%7D%23mermaid-_r_vt_%20.edge-thickness-normal%7Bstroke-width%3A1px%3B%7D%23mermaid-_r_vt_%20.edge-thickness-thick%7Bstroke-width%3A3.5px%3B%7D%23mermaid-_r_vt_%20.edge-pattern-solid%7Bstroke-dasharray%3A0%3B%7D%23mermaid-_r_vt_%20.edge-thickness-invisible%7Bstroke-width%3A0%3Bfill%3Anone%3B%7D%23mermaid-_r_vt_%20.edge-pattern-dashed%7Bstroke-dasharray%3A3%3B%7D%23mermaid-_r_vt_%20.edge-pattern-dotted%7Bstroke-dasharray%3A2%3B%7D%23mermaid-_r_vt_%20.marker%7Bfill%3Alightgrey%3Bstroke%3Alightgrey%3B%7D%23mermaid-_r_vt_%20.marker.cross%7Bstroke%3Alightgrey%3B%7D%23mermaid-_r_vt_%20svg%7Bfont-family%3A%22trebuchet%20ms%22%2Cverdana%2Carial%2Csans-serif%3Bfont-size%3A16px%3B%7D%23mermaid-_r_vt_%20p%7Bmargin%3A0%3B%7D%23mermaid-_r_vt_%20.label%7Bfont-family%3A%22trebuchet%20ms%22%2Cverdana%2Carial%2Csans-serif%3Bcolor%3A%23ccc%3B%7D%23mermaid-_r_vt_%20.cluster-label%20text%7Bfill%3A%23F9FFFE%3B%7D%23mermaid-_r_vt_%20.cluster-label%20span%7Bcolor%3A%23F9FFFE%3B%7D%23mermaid-_r_vt_%20.cluster-label%20span%20p%7Bbackground-color%3Atransparent%3B%7D%23mermaid-_r_vt_%20.label%20text%2C%23mermaid-_r_vt_%20span%7Bfill%3A%23ccc%3Bcolor%3A%23ccc%3B%7D%23mermaid-_r_vt_%20.node%20rect%2C%23mermaid-_r_vt_%20.node%20circle%2C%23mermaid-_r_vt_%20.node%20ellipse%2C%23mermaid-_r_vt_%20.node%20polygon%2C%23mermaid-_r_vt_%20.node%20path%7Bfill%3A%231f2020%3Bstroke%3A%23ccc%3Bstroke-width%3A1px%3B%7D%23mermaid-_r_vt_%20.rough-node%20.label%20text%2C%23mermaid-_r_vt_%20.node%20.label%20text%2C%23mermaid-_r_vt_%20.image-shape%20.label%2C%23mermaid-_r_vt_%20.icon-shape%20.label%7Btext-anchor%3Amiddle%3B%7D%23mermaid-_r_vt_%20.node%20.katex%20path%7Bfill%3A%23000%3Bstroke%3A%23000%3Bstroke-width%3A1px%3B%7D%23mermaid-_r_vt_%20.rough-node%20.label%2C%23mermaid-_r_vt_%20.node%20.label%2C%23mermaid-_r_vt_%20.image-shape%20.label%2C%23mermaid-_r_vt_%20.icon-shape%20.label%7Btext-align%3Acenter%3B%7D%23mermaid-_r_vt_%20.node.clickable%7Bcursor%3Apointer%3B%7D%23mermaid-_r_vt_%20.root%20.anchor%20path%7Bfill%3Alightgrey!important%3Bstroke-width%3A0%3Bstroke%3Alightgrey%3B%7D%23mermaid-_r_vt_%20.arrowheadPath%7Bfill%3Alightgrey%3B%7D%23mermaid-_r_vt_%20.edgePath%20.path%7Bstroke%3Alightgrey%3Bstroke-width%3A2.0px%3B%7D%23mermaid-_r_vt_%20.flowchart-link%7Bstroke%3Alightgrey%3Bfill%3Anone%3B%7D%23mermaid-_r_vt_%20.edgeLabel%7Bbackground-color%3Ahsl(0%2C%200%25%2C%2034.4117647059%25)%3Btext-align%3Acenter%3B%7D%23mermaid-_r_vt_%20.edgeLabel%20p%7Bbackground-color%3Ahsl(0%2C%200%25%2C%2034.4117647059%25)%3B%7D%23mermaid-_r_vt_%20.edgeLabel%20rect%7Bopacity%3A0.5%3Bbackground-color%3Ahsl(0%2C%200%25%2C%2034.4117647059%25)%3Bfill%3Ahsl(0%2C%200%25%2C%2034.4117647059%25)%3B%7D%23mermaid-_r_vt_%20.labelBkg%7Bbackground-color%3Argba(87.75%2C%2087.75%2C%2087.75%2C%200.5)%3B%7D%23mermaid-_r_vt_%20.cluster%20rect%7Bfill%3Ahsl(180%2C%201.5873015873%25%2C%2028.3529411765%25)%3Bstroke%3Argba(255%2C%20255%2C%20255%2C%200.25)%3Bstroke-width%3A1px%3B%7D%23mermaid-_r_vt_%20.cluster%20text%7Bfill%3A%23F9FFFE%3B%7D%23mermaid-_r_vt_%20.cluster%20span%7Bcolor%3A%23F9FFFE%3B%7D%23mermaid-_r_vt_%20div.mermaidTooltip%7Bposition%3Aabsolute%3Btext-align%3Acenter%3Bmax-width%3A200px%3Bpadding%3A2px%3Bfont-family%3A%22trebuchet%20ms%22%2Cverdana%2Carial%2Csans-serif%3Bfont-size%3A12px%3Bbackground%3Ahsl(20%2C%201.5873015873%25%2C%2012.3529411765%25)%3Bborder%3A1px%20solid%20rgba(255%2C%20255%2C%20255%2C%200.25)%3Bborder-radius%3A2px%3Bpointer-events%3Anone%3Bz-index%3A100%3B%7D%23mermaid-_r_vt_%20.flowchartTitleText%7Btext-anchor%3Amiddle%3Bfont-size%3A18px%3Bfill%3A%23ccc%3B%7D%23mermaid-_r_vt_%20rect.text%7Bfill%3Anone%3Bstroke-width%3A0%3B%7D%23mermaid-_r_vt_%20.icon-shape%2C%23mermaid-_r_vt_%20.image-shape%7Bbackground-color%3Ahsl(0%2C%200%25%2C%2034.4117647059%25)%3Btext-align%3Acenter%3B%7D%23mermaid-_r_vt_%20.icon-shape%20p%2C%23mermaid-_r_vt_%20.image-shape%20p%7Bbackground-color%3Ahsl(0%2C%200%25%2C%2034.4117647059%25)%3Bpadding%3A2px%3B%7D%23mermaid-_r_vt_%20.icon-shape%20rect%2C%23mermaid-_r_vt_%20.image-shape%20rect%7Bopacity%3A0.5%3Bbackground-color%3Ahsl(0%2C%200%25%2C%2034.4117647059%25)%3Bfill%3Ahsl(0%2C%200%25%2C%2034.4117647059%25)%3B%7D%23mermaid-_r_vt_%20.label-icon%7Bdisplay%3Ainline-block%3Bheight%3A1em%3Boverflow%3Avisible%3Bvertical-align%3A-0.125em%3B%7D%23mermaid-_r_vt_%20.node%20.label-icon%20path%7Bfill%3AcurrentColor%3Bstroke%3Arevert%3Bstroke-width%3Arevert%3B%7D%23mermaid-_r_vt_%20%3Aroot%7B--mermaid-font-family%3A%22trebuchet%20ms%22%2Cverdana%2Carial%2Csans-serif%3B%7D%3C%2Fstyle%3E%3Cg%3E%3Cmarker%20id%3D%22mermaid-_r_vt__flowchart-v2-pointEnd%22%20class%3D%22marker%20flowchart-v2%22%20viewBox%3D%220%200%2010%2010%22%20refX%3D%225%22%20refY%3D%225%22%20markerUnits%3D%22userSpaceOnUse%22%20markerWidth%3D%228%22%20markerHeight%3D%228%22%20orient%3D%22auto%22%3E%3Cpath%20d%3D%22M%200%200%20L%2010%205%20L%200%2010%20z%22%20class%3D%22arrowMarkerPath%22%20style%3D%22stroke-width%3A%201%3B%20stroke-dasharray%3A%201%2C%200%3B%22%3E%3C%2Fpath%3E%3C%2Fmarker%3E%3Cmarker%20id%3D%22mermaid-_r_vt__flowchart-v2-pointStart%22%20class%3D%22marker%20flowchart-v2%22%20viewBox%3D%220%200%2010%2010%22%20refX%3D%224.5%22%20refY%3D%225%22%20markerUnits%3D%22userSpaceOnUse%22%20markerWidth%3D%228%22%20markerHeight%3D%228%22%20orient%3D%22auto%22%3E%3Cpath%20d%3D%22M%200%205%20L%2010%2010%20L%2010%200%20z%22%20class%3D%22arrowMarkerPath%22%20style%3D%22stroke-width%3A%201%3B%20stroke-dasharray%3A%201%2C%200%3B%22%3E%3C%2Fpath%3E%3C%2Fmarker%3E%3Cmarker%20id%3D%22mermaid-_r_vt__flowchart-v2-circleEnd%22%20class%3D%22marker%20flowchart-v2%22%20viewBox%3D%220%200%2010%2010%22%20refX%3D%2211%22%20refY%3D%225%22%20markerUnits%3D%22userSpaceOnUse%22%20markerWidth%3D%2211%22%20markerHeight%3D%2211%22%20orient%3D%22auto%22%3E%3Ccircle%20cx%3D%225%22%20cy%3D%225%22%20r%3D%225%22%20class%3D%22arrowMarkerPath%22%20style%3D%22stroke-width%3A%201%3B%20stroke-dasharray%3A%201%2C%200%3B%22%3E%3C%2Fcircle%3E%3C%2Fmarker%3E%3Cmarker%20id%3D%22mermaid-_r_vt__flowchart-v2-circleStart%22%20class%3D%22marker%20flowchart-v2%22%20viewBox%3D%220%200%2010%2010%22%20refX%3D%22-1%22%20refY%3D%225%22%20markerUnits%3D%22userSpaceOnUse%22%20markerWidth%3D%2211%22%20markerHeight%3D%2211%22%20orient%3D%22auto%22%3E%3Ccircle%20cx%3D%225%22%20cy%3D%225%22%20r%3D%225%22%20class%3D%22arrowMarkerPath%22%20style%3D%22stroke-width%3A%201%3B%20stroke-dasharray%3A%201%2C%200%3B%22%3E%3C%2Fcircle%3E%3C%2Fmarker%3E%3Cmarker%20id%3D%22mermaid-_r_vt__flowchart-v2-crossEnd%22%20class%3D%22marker%20cross%20flowchart-v2%22%20viewBox%3D%220%200%2011%2011%22%20refX%3D%2212%22%20refY%3D%225.2%22%20markerUnits%3D%22userSpaceOnUse%22%20markerWidth%3D%2211%22%20markerHeight%3D%2211%22%20orient%3D%22auto%22%3E%3Cpath%20d%3D%22M%201%2C1%20l%209%2C9%20M%2010%2C1%20l%20-9%2C9%22%20class%3D%22arrowMarkerPath%22%20style%3D%22stroke-width%3A%202%3B%20stroke-dasharray%3A%201%2C%200%3B%22%3E%3C%2Fpath%3E%3C%2Fmarker%3E%3Cmarker%20id%3D%22mermaid-_r_vt__flowchart-v2-crossStart%22%20class%3D%22marker%20cross%20flowchart-v2%22%20viewBox%3D%220%200%2011%2011%22%20refX%3D%22-1%22%20refY%3D%225.2%22%20markerUnits%3D%22userSpaceOnUse%22%20markerWidth%3D%2211%22%20markerHeight%3D%2211%22%20orient%3D%22auto%22%3E%3Cpath%20d%3D%22M%201%2C1%20l%209%2C9%20M%2010%2C1%20l%20-9%2C9%22%20class%3D%22arrowMarkerPath%22%20style%3D%22stroke-width%3A%202%3B%20stroke-dasharray%3A%201%2C%200%3B%22%3E%3C%2Fpath%3E%3C%2Fmarker%3E%3Cg%20class%3D%22root%22%3E%3Cg%20class%3D%22clusters%22%3E%3C%2Fg%3E%3Cg%20class%3D%22edgePaths%22%3E%3Cpath%20d%3D%22M36.996%2C55.92L35.384%2C61.913C33.772%2C67.907%2C30.549%2C79.893%2C30.376%2C91.236C30.202%2C102.579%2C33.08%2C113.278%2C34.519%2C118.628L35.957%2C123.977%22%20id%3D%22L_A_B_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_A_B_0%22%20data-points%3D%22W3sieCI6MzYuOTk2MTUwNDA1NDgxMTEsInkiOjU1LjkxOTk5ODE2ODk0NTMxfSx7IngiOjI3LjMyNDk5ODg1NTU5MDgyLCJ5Ijo5MS44Nzk5OTgyMDcwOTIyOX0seyJ4IjozNi45OTYxNTA0MDU0ODExMSwieSI6MTI3LjgzOTk5ODI0NTIzOTI2fV0%3D%22%20marker-end%3D%22url(%23mermaid-_r_vt__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M49.884%2C127.84L51.496%2C121.847C53.108%2C115.853%2C56.331%2C103.867%2C56.504%2C92.524C56.678%2C81.181%2C53.8%2C70.482%2C52.361%2C65.132L50.923%2C59.783%22%20id%3D%22L_B_A_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_B_A_0%22%20data-points%3D%22W3sieCI6NDkuODgzODQ2ODQ3OTM2ODYsInkiOjEyNy44Mzk5OTgyNDUyMzkyNn0seyJ4Ijo1OS41NTQ5OTgzOTc4MjcxNSwieSI6OTEuODc5OTk4MjA3MDkyMjl9LHsieCI6NDkuODgzODQ2ODQ3OTM2ODYsInkiOjU1LjkxOTk5ODE2ODk0NTMxfV0%3D%22%20marker-end%3D%22url(%23mermaid-_r_vt__flowchart-v2-pointEnd)%22%3E%3C%2Fpath%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabels%22%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_A_B_0%22%20transform%3D%22translate(0%2C%200)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%20transform%3D%22translate(59.55499839782715%2C%2091.87999820709229)%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_B_A_0%22%20transform%3D%22translate(-12.229999542236328%2C%20-10.960000038146973)%22%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22%22%20x%3D%22-2%22%20y%3D%22-0.08000004291534424%22%20width%3D%2224.459999084472656%22%20height%3D%2221.920000076293945%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3ENo%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22nodes%22%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-A-0%22%20transform%3D%22translate(43.439998626708984%2C%2031.959999084472656)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-35.44000005722046%22%20y%3D%22-23.960000038146973%22%20width%3D%2270.88000011444092%22%20height%3D%2247.920000076293945%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-8.960000038146973)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EA%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-B-1%22%20transform%3D%22translate(43.439998626708984%2C%20151.7999973297119)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-35.33999967575073%22%20y%3D%22-23.960000038146973%22%20width%3D%2270.67999935150146%22%20height%3D%2247.920000076293945%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate(0%2C%20-8.960000038146973)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EB%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fsvg%3E)

Use:

```Markdown
| Current state | Condition | Action | Next state |
|---|---|---|---|
| AwaitingReview | Approved | Commit final document | Accepted |
| AwaitingReview | Rejected and round < 5 | Revise and increment round | AwaitingReview |
| AwaitingReview | Rejected and round = 5 | Stop and surface blockers | Blocked |
```

This makes missing exits, infinite loops, and ambiguous transitions much easier to spot. For agent standards, I would make this the **source of truth** and generate Mermaid from it only when you want a visual.

### 5. Decision tables for branching rules

Decision tables are ideal when the agent has to choose between actions based on conditions. DMN is the formal standard in this space; OMG describes DMN as a modeling language for precise specification of business decisions and rules. [![](https://www.google.com/s2/favicons?domain=https://www.omg.org&sz=128)OMG](https://www.omg.org/dmn/?utm_source=chatgpt.com)

A lightweight Markdown version is enough for agents:

```Markdown
| Condition | Action | Priority |
|---|---|---:|
| Tests fail | Fix failing tests before continuing | 1 |
| Tests pass and docs changed | Run docs validation | 2 |
| Tests pass and no docs changed | Proceed to review | 3 |
| Required input missing | Stop and ask for the missing input | 0 |
```

Decision tables are often better than prose because they force you to enumerate cases.

### 6. BPMN when the audience is business/process-heavy

BPMN is a mature standard for business process diagrams. OMG describes it as a de facto standard for business process diagrams, intended to be understandable to stakeholders while still precise enough to translate into software process components. [![](https://www.google.com/s2/favicons?domain=https://www.omg.org&sz=128)OMG](https://www.omg.org/spec/BPMN/2.0.2/About-BPMN)

For your agent standards, I would not make BPMN the default. It is useful when communicating with process/business stakeholders, but for LLM-agent execution, Markdown state tables are usually cheaper, clearer, and more diff-friendly.

## My recommended stack for agent instructions

Use this hierarchy:

```Markdown
1. Plain English intent
2. RFC 2119 rules
3. State transition table
4. Decision table for branching
5. Gherkin examples for expected behavior
6. Optional Mermaid generated from the table
```

That gives you determinism without requiring perfect diagram syntax.

## Practical rule

Use this mapping:

| What you need to express | Use |
| --- | --- |
| “What must be true?” | RFC 2119 rule |
| “When X happens, what should the system do?” | EARS-style sentence |
| “How does the process move from step to step?” | State transition table |
| “Which branch should be chosen?” | Decision table |
| “What does correct behavior look like?” | Gherkin scenario |
| “What does the process look like visually?” | Mermaid/BPMN/PlantUML |
| “What data shape is valid?” | JSON Schema / Pydantic model |

The key point: **make the Markdown table the deterministic artifact, not the diagram.** Diagrams are great views. They are weak source-of-truth documents unless the syntax is validated and the diagram fully encodes guards, counters, exits, and failure handling.

* * *

**You:**

What would be best for instructions that involve a lot of if then else statements and while and four loops. My personal familiarity is with python and that structure makes most sense to me.

* * *

**ChatGPT:**

Use **Python-like structured pseudocode** as your primary instruction language.

Given your familiarity with Python, that is probably the best fit. LLM agents understand Pythonic control flow very well, indentation carries meaning, and `if / elif / else`, `while`, and `for` map cleanly to process instructions. The trick is: **do not write fake executable Python unless you actually intend it to run.** Use a restrained “pseudo-Python” convention.

## Best format: pseudo-Python plus explicit semantics

Example:

```Python
process amend_document(document, reviewer, max_rounds=5):
    round = 1
    blockers = []

    while round <= max_rounds:
        review = reviewer.review(document)

        if review.status == "approved":
            commit(document)
            return Accepted

        elif review.status == "rejected" and review.blockers:
            blockers = review.blockers
            document = revise(document, blockers)
            round += 1
            continue

        else:
            return Blocked(reason="review returned invalid or ambiguous status")

    return Blocked(
        reason="round cap reached",
        unresolved_blockers=blockers,
    )
```

That is much clearer to an agent than longform prose like:

> Keep revising until the reviewer approves it, but don’t do that forever, and if it still has issues after a few rounds, stop and explain the problem.

The pseudocode version makes these things explicit:

* loop boundary
* success condition
* retry condition
* failure condition
* state variables
* return states
* what gets carried forward between rounds

## The convention I’d use

Define a small pseudo-Python grammar in your standards:

```Python
process <name>(inputs):
    # Declare state
    variable = initial_value

    # Main control flow
    if condition:
        action()
    elif condition:
        action()
    else:
        fallback()

    while condition:
        action()
        update_loop_state()

    for item in collection:
        action(item)

    return Outcome(...)
```

Then document that:

```Markdown
- `process` defines an agent workflow, not executable Python.
- Function calls such as `review()`, `revise()`, and `commit()` are required agent actions.
- `return` exits the process immediately.
- `continue` repeats the current loop.
- `break` exits the current loop.
- All `while` loops MUST have an explicit cap or externally defined stop condition.
- All branches MUST end in an action, transition, or return.
```

That gives you determinism without requiring valid Python modules, imports, classes, or perfect runtime syntax.

## Use pseudo-Python for flow; use tables for large condition sets

Pseudo-Python is best when the process has **sequence and state**:

```Python
while round <= 5:
    if approved:
        return Accepted
    else:
        revise()
```

But if you have many independent conditions, a decision table is better than a giant nested `if`.

Bad:

```Python
if public_repo and protected_branch and release_change:
    ...
elif public_repo and protected_branch and no_release_change:
    ...
elif private_repo and protected_branch and release_change:
    ...
elif private_repo and not protected_branch:
    ...
```

Better:

| Repo type | Branch protected? | Release change? | Required action |
| --- | --- | --- | --- |
| Public | Yes | Yes | Require explicit user approval |
| Public | Yes | No | Require CI pass |
| Private | Yes | Yes | Require explicit user approval |
| Private | No | Any | Stop and surface repo policy defect |

Then the pseudocode can reference the table:

```Python
decision = lookup_required_action(repo_type, branch_protected, release_change)

if decision == "require_user_approval":
    ask_user_inline()
elif decision == "require_ci_pass":
    run_ci_checks()
elif decision == "stop_policy_defect":
    return Blocked(reason="repo policy defect")
```

That keeps the process readable.

## Recommended structure for agent standards

For complex instructions, I would standardize this pattern:

````Markdown
# Process: <name>

## Purpose
Brief explanation.

## Inputs
- document
- reviewer
- max_rounds

## Outputs
- Accepted
- Blocked
- NeedsUserDecision

## Pseudocode

```python
process ...
````

## Invariants

* The agent MUST NOT exceed `max_rounds`.
* The agent MUST preserve unresolved blockers across rounds.
* The agent MUST stop on ambiguous reviewer output.

## Decision tables

Tables for large branching rules.

## Examples

Concrete examples of expected behavior.

````

The pseudocode is the control-flow source of truth. The prose explains intent. The invariants catch edge cases.

## Important cautions

### 1. Avoid deeply nested `if` blocks

Agents handle this:

```python
if condition_a:
    if condition_b:
        if condition_c:
            do_thing()
````

But humans and agents both misread it eventually. Prefer guard clauses:

```Python
if missing_required_input:
    return Blocked(reason="missing input")

if round > max_rounds:
    return Blocked(reason="round cap reached")

if approved:
    return Accepted

revise()
```

### 2. Every loop needs a cap

Never write:

```Python
while not approved:
    revise()
```

Write:

```Python
while not approved and round <= max_rounds:
    revise()
    round += 1

if not approved:
    return Blocked(reason="round cap reached")
```

This matters a lot for agent workflows.

### 3. Make side effects explicit

Bad:

```Python
fix_issue()
```

Better:

```Python
fix_issue()
run_tests()
if tests_pass:
    commit_changes()
else:
    return Blocked(reason="tests failed")
```

Agents need to know which actions mutate files, create commits, open PRs, ask the user, or stop execution.

### 4. Do not rely only on comments

Bad:

```Python
# Review it and fix stuff until good
while True:
    ...
```

Better:

```Python
while review.status != "approved" and round <= max_rounds:
    ...
```

The executable-looking control flow should carry the actual rules.

## My recommendation

For your standards, use this as the default:

> **Pythonic structured pseudocode for flow control, Markdown tables for large condition matrices, and RFC-style MUST/SHOULD rules for invariants.**

That gives you a strong balance:

* familiar to you
* easy for agents to parse
* diff-friendly
* less syntax-sensitive than Mermaid
* more deterministic than prose
* suitable for if/else, loops, counters, retries, and stop conditions

* * *

**You:**

Are there any published standards or generally accepted, conventions for Python structured pseudocode

* * *

**ChatGPT:**

I’ll verify this against published sources, but the likely answer is: no single Python-pseudocode standard; the defensible approach is to adopt Python syntax conventions plus a small local pseudocode contract.

There is **no formal, widely accepted standard called “Python structured pseudocode.”** The defensible version is a **local convention** based on:

1. **Python control-flow syntax** for structure.
2. **PEP 8** for readability and naming.
3. **Published pseudocode conventions** for concepts like assignment, selection, iteration, procedures, and return.
4. A short local “this is pseudocode, not executable Python” contract.

Python’s official language reference already gives you the strongest anchor: `if`, `while`, and `for` are the traditional control-flow constructs, and Python compound statements use clause headers ending in colons with indented suites underneath. That maps almost perfectly to process instructions for agents. [![](https://www.google.com/s2/favicons?domain=https://docs.python.org&sz=128)Python documentation](https://docs.python.org/3/reference/compound_stmts.html)

PEP 8 is not a pseudocode standard, but it is the official Python style guide for readability and consistency, and it explicitly says project-specific style guides take precedence. That makes it reasonable to define your own “Pythonic pseudocode” project convention while borrowing Python naming and layout expectations. [![](https://www.google.com/s2/favicons?domain=https://peps.python.org&sz=128)Python Enhancement Proposals (PEPs)](https://peps.python.org/pep-0008/)

## Published things that are adjacent

| Source | What it gives you | Usefulness for your case |
| --- | --- | --- |
| **Python Language Reference** | Official semantics for `if`, `while`, `for`, `try`, `with`, `return`, indentation, clauses | Best anchor for Python-shaped pseudocode |
| **PEP 8** | Naming, readability, consistency, project-local convention precedence | Good style baseline |
| **College Board AP CSP pseudocode** | Published educational pseudocode for assignment, `IF`, `ELSE`, `REPEAT`, `FOR EACH`, procedures, `RETURN` | Good proof that structured pseudocode conventions exist |
| **Cambridge pseudocode guide** | Detailed pseudocode grammar for assignment, selection, `CASE`, `FOR`, `WHILE`, procedures, functions, return behavior | Useful reference, but not Pythonic |
| **Program Design Language / Structured English** | Older structured-programming convention built around sequence, while, if-then-else, repeat-until, for, case | Conceptually useful, not a modern Python standard |

College Board’s AP CSP reference is a good example of a controlled pseudocode dialect: it defines assignment, `IF`/`ELSE`, `REPEAT`, `FOR EACH`, procedures, and `RETURN`. But it is intentionally language-neutral, not Pythonic. [![](https://www.google.com/s2/favicons?domain=https://apcentral.collegeboard.org&sz=128)AP Central](https://apcentral.collegeboard.org/media/pdf/ap-computer-science-principles-exam-reference-sheet.pdf)

Cambridge’s guide is even more formal, with assignment using `←`, `IF ... THEN ... ENDIF`, `CASE`, `FOR ... NEXT`, `WHILE ... ENDWHILE`, and procedure/function forms. Again, useful as a reference, but I would not adopt it for your agent instructions because it fights your Python mental model. [![](https://www.google.com/s2/favicons?domain=https://www.cambridgeinternational.org&sz=128)Cambridge International](https://www.cambridgeinternational.org/Images/697401-2026-pseudocode-guide-for-teachers.pdf)

## Best practical standard for you

Use a **Pythonic pseudocode subset** and define it explicitly.

```Python
# PSEUDOCODE: Python-shaped process instruction, not executable Python.

def process_name(input_a, input_b, max_rounds=5) -> Outcome:
    state = initial_state()

    for round in range(1, max_rounds + 1):
        result = perform_review(state)

        if result.approved:
            commit_final_result(state)
            return Accepted(reason="approved")

        elif result.blockers:
            state = revise_using_blockers(state, result.blockers)
            continue

        else:
            return Blocked(reason="ambiguous review result")

    return Blocked(reason="round cap reached")
```

Then define the convention once:

```Markdown
## Pythonic pseudocode convention

- This is pseudocode, not executable Python.
- Python indentation is semantically meaningful.
- `def` defines a workflow or subroutine.
- `if / elif / else` define exclusive branches.
- `for` iterates over a known collection or bounded range.
- `while` repeats until its condition is false.
- Every `while` loop MUST include a cap, timeout, or explicit stop condition.
- `return` exits the process immediately.
- Function calls represent required agent actions.
- Variables represent workflow state, not necessarily real Python objects.
- Comments explain intent but MUST NOT contain the only copy of a requirement.
```

That gives you a convention that is easy for you, easy for agents, and defensible against published references without pretending there is an official Python pseudocode standard.

## My recommendation

Do **not** adopt AP CSP, Cambridge, or generic academic pseudocode wholesale. They are more foreign to your Python instincts than necessary.

Use this stack instead:

```Markdown
Python Language Reference semantics
+ PEP 8 readability
+ local Pythonic pseudocode contract
+ RFC-style MUST/SHOULD rules for invariants
+ decision tables when branching gets too wide
```

The important line to draw is this:

> If it must be validated by a machine, write real Python with stubs and tests. If it must guide an agent, use Python-shaped pseudocode with an explicit local contract.

* * *

**You:**

I want you to create a markdown document and provide me a download link for it. This document should be a comprehensive Python pseudo code standard.  It should be a complete guide with all information. I need to use it as if it were a comprehensive textbook.  Include sources for the parts that can be sourced and annotate where it’s truly internal convention.

* * *

**ChatGPT:**

I’ll produce this as a standalone Markdown standard with normative sections, examples, validation checklists, and a source map. I’ll separate sourced foundations from internal convention so the document can be adopted as a project standard without overclaiming.

Done. I created the Markdown document here:

It includes sourced foundations, internal-convention annotations, rules, examples, lint checks, templates, and a source list.

* * *

**You:**

What are the logistics of creating a syntax highlighting plug-in for this pseudo language for VS code or Kate?

* * *

**ChatGPT:**

Best logistics: **define the pseudocode language once as a token/spec table, then implement two editor adapters**:

1. **VS Code adapter**: TextMate grammar extension.
2. **Kate adapter**: KSyntaxHighlighting XML definition.
3. Optional later: formatter/linter/parser, but do not start there.

For your Python-like pseudocode, a syntax highlighter is very practical. You do **not** need a full language server unless you want diagnostics like “this `while` loop has no cap.”

## Recommended architecture

Use this structure in your standards repo:

```
agent-pseudocode-syntax/
├── language-spec/
│   ├── tokens.md
│   ├── examples/
│   │   ├── valid-basic.apseudo
│   │   ├── valid-review-loop.apseudo
│   │   └── invalid-unbounded-loop.apseudo
│   └── scope-map.md
├── vscode/
│   ├── package.json
│   ├── language-configuration.json
│   └── syntaxes/
│       ├── agent-pseudocode.tmLanguage.yaml
│       └── agent-pseudocode.tmLanguage.json
└── kate/
    └── agent-pseudocode.xml
```

The **source of truth** should not be the VS Code grammar or the Kate XML. It should be a small language-spec document that says:

```Markdown
| Concept | Lexeme examples | VS Code/TextMate scope | Kate style |
|---|---|---|---|
| Control keyword | if, elif, else, while, for, return, continue, break | keyword.control.agent-pseudocode | ControlFlow |
| Normative keyword | MUST, SHOULD, MAY, MUST NOT | keyword.other.normative.agent-pseudocode | Alert |
| Outcome constructor | Accepted, Blocked, NeedsUserDecision | support.class.outcome.agent-pseudocode | DataType |
| Agent action | review(), revise(), commit() | entity.name.function.agent-pseudocode | Function |
| Comment | # comment | comment.line.number-sign.agent-pseudocode | Comment |
```

That avoids drift between the two editors.

## VS Code path

VS Code syntax highlighting is based primarily on **TextMate grammars**. Microsoft’s docs say VS Code uses TextMate grammars for tokenization, that they are regular-expression-based, and that extensions contribute them through the `grammars` contribution point. [![](https://www.google.com/s2/favicons?domain=https://code.visualstudio.com&sz=128)Visual Studio Code](https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide)

### What you build

A minimal VS Code extension needs:

```
vscode/
├── package.json
├── language-configuration.json
└── syntaxes/
    └── agent-pseudocode.tmLanguage.json
```

The extension contributes two things:

1. A language ID, file extensions, and aliases.
2. A grammar file that maps regex matches to TextMate scopes.

VS Code’s `contributes.languages` associates file extensions and related metadata with a language ID, and `contributes.grammars` maps that language to a TextMate grammar path and scope name. [![](https://www.google.com/s2/favicons?domain=https://code.visualstudio.com&sz=128)Visual Studio Code](https://code.visualstudio.com/api/references/contribution-points)

Example `package.json` shape:

```JSON
{
  "name": "agent-pseudocode",
  "displayName": "Agent Pseudocode",
  "description": "Syntax highlighting for Pythonic agent pseudocode.",
  "version": "0.1.0",
  "publisher": "l3digital",
  "engines": {
    "vscode": "^1.90.0"
  },
  "categories": ["Programming Languages"],
  "contributes": {
    "languages": [
      {
        "id": "agent-pseudocode",
        "aliases": ["Agent Pseudocode", "apseudo"],
        "extensions": [".apseudo", ".agentpseudo"],
        "configuration": "./language-configuration.json"
      }
    ],
    "grammars": [
      {
        "language": "agent-pseudocode",
        "scopeName": "source.agent-pseudocode",
        "path": "./syntaxes/agent-pseudocode.tmLanguage.json"
      }
    ]
  }
}
```

Example grammar fragment:

```JSON
{
  "scopeName": "source.agent-pseudocode",
  "patterns": [
    { "include": "#comments" },
    { "include": "#normative" },
    { "include": "#control" },
    { "include": "#outcomes" },
    { "include": "#functions" },
    { "include": "#strings" }
  ],
  "repository": {
    "comments": {
      "patterns": [
        {
          "name": "comment.line.number-sign.agent-pseudocode",
          "match": "#.*$"
        }
      ]
    },
    "control": {
      "patterns": [
        {
          "name": "keyword.control.agent-pseudocode",
          "match": "\\b(if|elif|else|while|for|in|return|continue|break|try|except|finally)\\b"
        }
      ]
    },
    "normative": {
      "patterns": [
        {
          "name": "keyword.other.normative.agent-pseudocode",
          "match": "\\b(MUST NOT|MUST|SHOULD NOT|SHOULD|MAY|OPTIONAL|REQUIRED)\\b"
        }
      ]
    },
    "outcomes": {
      "patterns": [
        {
          "name": "support.class.outcome.agent-pseudocode",
          "match": "\\b(Accepted|Blocked|NeedsUserDecision|Rejected|Approved)\\b"
        }
      ]
    },
    "functions": {
      "patterns": [
        {
          "name": "entity.name.function.agent-pseudocode",
          "match": "\\b[a-zA-Z_][a-zA-Z0-9_]*(?=\\()"
        }
      ]
    },
    "strings": {
      "patterns": [
        {
          "name": "string.quoted.double.agent-pseudocode",
          "begin": "\"",
          "end": "\""
        }
      ]
    }
  }
}
```

For maintainability, I would author the grammar in YAML and compile to JSON. VS Code can only load JSON grammars, but Microsoft’s docs explicitly suggest YAML as a maintainable authoring format that is converted to JSON. [![](https://www.google.com/s2/favicons?domain=https://code.visualstudio.com&sz=128)Visual Studio Code](https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide)

### Markdown fenced code blocks

This matters for your use case because your pseudocode will often live inside `.md` standards.

Use a fence name like:

````Markdown
```agent-pseudocode
process amend_document(...):
    ...
```
````

or shorter:

````Markdown
```apseudo
process amend_document(...):
    ...
```
````

For robust Markdown support, use a VS Code **injection grammar** if normal language registration is not enough. VS Code docs explicitly list “adding highlighting for a new language to Markdown fenced code blocks” as a use case for injection grammars. [![](https://www.google.com/s2/favicons?domain=https://code.visualstudio.com&sz=128)Visual Studio Code](https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide)

My recommendation: support both:

* standalone files: `.apseudo`
* Markdown fences: `agent-pseudocode` and `apseudo`

### Debugging

VS Code has a built-in token/scope inspector: `Developer: Inspect Editor Tokens and Scopes`. That is the main debugging loop for whether your regex matched and whether the assigned scope is theme-compatible. [![](https://www.google.com/s2/favicons?domain=https://code.visualstudio.com&sz=128)Visual Studio Code](https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide)

## Kate path

Kate uses KDE’s **KSyntaxHighlighting** framework. KatePart syntax definitions are XML files containing detection rules, keyword lists, and style definitions. [![](https://www.google.com/s2/favicons?domain=https://docs.kde.org&sz=128)KDE Documentation](https://docs.kde.org/stable_kf6/en/kate/katepart/highlight.html)

### What you build

For Kate, you write one XML file:

```
kate/agent-pseudocode.xml
```

Kate’s docs say the XML definition has a root `language` element with required attributes such as `name`, `section`, `extensions`, `version`, and `kateversion`; if multiple definitions match, higher `version` or priority can matter. [![](https://www.google.com/s2/favicons?domain=https://docs.kde.org&sz=128)KDE Documentation](https://docs.kde.org/stable_kf6/en/kate/katepart/highlight.html)

Example shape:

```XML
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE language SYSTEM "language.dtd">

<language
    name="Agent Pseudocode"
    section="Markup"
    extensions="*.apseudo;*.agentpseudo"
    version="1"
    kateversion="5.0"
    casesensitive="1"
    author="Chris Purcell"
    license="MIT">

  <highlighting>
    <list name="control_keywords">
      <item>if</item>
      <item>elif</item>
      <item>else</item>
      <item>while</item>
      <item>for</item>
      <item>in</item>
      <item>return</item>
      <item>continue</item>
      <item>break</item>
      <item>try</item>
      <item>except</item>
      <item>finally</item>
    </list>

    <list name="normative_keywords">
      <item>MUST</item>
      <item>SHOULD</item>
      <item>MAY</item>
      <item>OPTIONAL</item>
      <item>REQUIRED</item>
    </list>

    <list name="outcomes">
      <item>Accepted</item>
      <item>Blocked</item>
      <item>NeedsUserDecision</item>
      <item>Approved</item>
      <item>Rejected</item>
    </list>

    <contexts>
      <context name="Normal" attribute="Normal Text" lineEndContext="#stay">
        <DetectChar char="#" attribute="Comment" context="Comment"/>
        <keyword String="control_keywords" attribute="ControlFlow" context="#stay"/>
        <keyword String="normative_keywords" attribute="Normative" context="#stay"/>
        <keyword String="outcomes" attribute="Outcome" context="#stay"/>
        <DetectChar char="&quot;" attribute="String" context="String"/>
      </context>

      <context name="Comment" attribute="Comment" lineEndContext="#pop"/>

      <context name="String" attribute="String" lineEndContext="#pop">
        <DetectChar char="&quot;" attribute="String" context="#pop"/>
      </context>
    </contexts>

    <itemDatas>
      <itemData name="Normal Text" defStyleNum="dsNormal"/>
      <itemData name="Comment" defStyleNum="dsComment"/>
      <itemData name="String" defStyleNum="dsString"/>
      <itemData name="ControlFlow" defStyleNum="dsControlFlow"/>
      <itemData name="Normative" defStyleNum="dsAlert"/>
      <itemData name="Outcome" defStyleNum="dsDataType"/>
    </itemDatas>
  </highlighting>

  <general>
    <comments>
      <comment name="singleLine" start="#"/>
    </comments>
  </general>
</language>
```

Kate’s framework models a syntax definition as an XML-backed definition containing highlighting information, keywords, code folding, indentation preferences, comment markers, and similar editor-facing metadata. [![](https://www.google.com/s2/favicons?domain=https://api.kde.org&sz=128)KDE API](https://api.kde.org/ksyntaxhighlighting-definition.html)

### Install locations

Kate custom XML files go under the user syntax-highlighting data directory. The docs list the common local Linux path as:

```
$HOME/.local/share/org.kde.syntax-highlighting/syntax/
```

They also list paths for system-wide installs, Flatpak, Snap, Windows, and macOS. [![](https://www.google.com/s2/favicons?domain=https://docs.kde.org&sz=128)KDE Documentation](https://docs.kde.org/stable_kf6/en/kate/katepart/highlight.html)

For your Fedora/KDE workstation, the practical install command is likely:

```Bash
mkdir -p "$HOME/.local/share/org.kde.syntax-highlighting/syntax"
cp kate/agent-pseudocode.xml "$HOME/.local/share/org.kde.syntax-highlighting/syntax/"
```

Then restart Kate or reload highlighting definitions.

## Important limitation: highlighting is not validation

TextMate grammars and Kate XML rules are mostly regex/context highlighters. They can color `while`, `return`, `MUST`, `Blocked`, comments, strings, and action calls. They should **not** be expected to prove that a loop is bounded or that every branch returns. TextMate language grammars assign names/scopes to document elements for styling and editor behavior; they are not full semantic validators. [![](https://www.google.com/s2/favicons?domain=https://manual.macromates.com&sz=128)TextMate Manual](https://manual.macromates.com/en/language_grammars)

So split the project into layers:

| Layer | Purpose | Tool |
| --- | --- | --- |
| Syntax highlighting | Make pseudocode readable | VS Code TextMate grammar; Kate XML |
| Snippets | Insert standard blocks | VS Code snippets; Kate snippets/templates |
| Structural linting | Catch unbounded loops, missing returns, bad outcomes | Python CLI using tree-sitter/regex/parser |
| Formatting | Normalize indentation and spacing | Python CLI |
| Rich semantics | Hover docs, diagnostics, completion | Language Server Protocol |

Start with highlighting and snippets. Add a linter only when the standard stabilizes.

## Scope of the first version

Do not try to highlight every possible pseudo-Python construct. Version 1 should recognize:

```
Comments:
  # ...

Control flow:
  if, elif, else, while, for, in, return, continue, break

Process declarations:
  process name(...):
  def name(...):

Normative terms:
  MUST, MUST NOT, SHOULD, SHOULD NOT, MAY, REQUIRED, OPTIONAL

Outcomes:
  Accepted, Blocked, NeedsUserDecision, Rejected, Approved

Agent actions:
  lower_snake_case(...)

Literals:
  strings, numbers, booleans, None

Operators:
  ==, !=, <=, >=, <, >, =, and, or, not

Special process concepts:
  max_rounds, round, blockers, guard, invariant, stop_condition
```

That is enough to make your standards documents much easier to scan without overengineering a language.

## Recommended implementation order

1. **Freeze a tiny token spec**  
    Decide the canonical language IDs: `agent-pseudocode` and `apseudo`.
2. **Build VS Code first**  
    It has the better extension workflow and debugging tools. Use a TextMate grammar, not a language server.
3. **Add Markdown fence support**  
    This matters more than standalone `.apseudo` files because your standards are Markdown-heavy.
4. **Port to Kate XML**  
    Implement the same token categories using Kate keyword lists and context rules.
5. **Add a fixture corpus**  
    Keep 10–20 example pseudocode blocks and screenshot/token-inspection expectations.
6. **Add install scripts**  
    Use bash for local install:
    * VS Code: package/install extension locally.
    * Kate: copy XML into the syntax directory.
7. **Only then consider a linter**  
    A linter is where rules like “every `while` loop MUST have a cap” belong.

## My recommendation

Use **VS Code TextMate grammar + Kate KSyntaxHighlighting XML**, both generated or maintained from a shared token map.

For your actual workflow, I would make the pseudocode blocks look like this:

````Markdown
```apseudo
process amend_document(document, max_rounds=5):
    round = 1

    while round <= max_rounds:
        review = review_document(document)

        if review.status == "approved":
            return Accepted(reason="approved")

        elif review.blockers:
            document = revise(document, review.blockers)
            round += 1
            continue

        else:
            return Blocked(reason="ambiguous review result")

    return Blocked(reason="round cap reached")
```
````

Then the highlighter makes `process`, `while`, `if`, `elif`, `return`, `Accepted`, `Blocked`, and `MUST`-style terms visually distinct. That gives you most of the readability benefit with low maintenance cost.

* * *

**You:**

Create this. Include everything necessary for the VS code extension, including the markdown injection and Yamel to Jason Parser. Also include all of the documents I need for Kate.  And include an overall instruction document to myself to guide. Give me guidance on where I need to apply these install these and what other work I need to do to actually get this functional.

* * *

**ChatGPT:**

I’ll create a ready-to-drop-in project with VS Code, Markdown injection, YAML-to-JSON build tooling, Kate XML, install scripts, examples, tests, and a guide.

I’ve confirmed the editor-specific mechanics: VS Code will use TextMate JSON generated from YAML with Markdown fence injection, and Kate will use KSyntaxHighlighting XML.

Done. I created the full project bundle here:

I also left the expanded folder here for direct browsing/use in the sandbox:

I validated the generated grammar files and Kate XML statically in the container:

```Bash
./scripts/build-grammars.py
./scripts/check-fixtures.py
python3 -m json.tool vscode/package.json
python3 -m json.tool vscode/syntaxes/agent-pseudocode.tmLanguage.json
python3 -m json.tool vscode/syntaxes/agent-pseudocode-markdown-injection.tmLanguage.json
```

The zip includes:

| Area | Included |
| --- | --- |
| VS Code extension | `vscode/package.json`, `language-configuration.json`, snippets, TextMate JSON grammars |
| Markdown injection | `vscode/syntaxes/agent-pseudocode-markdown-injection.tmLanguage.yaml/json` |
| YAML → JSON compiler | `scripts/build-grammars.py` using PyYAML |
| Kate support | `kate/agent-pseudocode.xml` |
| Install scripts | `scripts/install-vscode-unpacked.sh`, `scripts/install-kate.sh`, `scripts/package-vscode-vsix.sh` |
| Guidance docs | `docs/INSTALL.md`, `docs/SELF-INSTRUCTIONS.md`, `docs/VSCODE-GUIDE.md`, `docs/KATE-GUIDE.md`, `docs/TOKEN-SPEC.md`, `docs/SCOPE-MAP.md`, `docs/SOURCES.md` |
| Examples/tests | `.apseudo` examples and Markdown fenced-block examples |

The implementation follows VS Code’s documented TextMate grammar model, YAML-authored grammar conversion to JSON, and injection grammar support for Markdown fenced blocks. [![](https://www.google.com/s2/favicons?domain=https://code.visualstudio.com&sz=128)Visual Studio Code+1](https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide) Kate support follows KDE/Kate’s XML syntax-definition model and the documented local install locations under `org.kde.syntax-highlighting/syntax/`. [![](https://www.google.com/s2/favicons?domain=https://docs.kde.org&sz=128)KDE Documentation+1](https://docs.kde.org/?application=katepart&branch=stable5&path=highlight.html)

Fast path after unzipping:

```Bash
cd agent-pseudocode-syntax

uv sync
./scripts/build-grammars.py
./scripts/check-fixtures.py
./scripts/install-vscode-unpacked.sh
./scripts/install-kate.sh
```

Then restart VS Code and Kate.

Important caveat: I validated the file structure, YAML/JSON generation, JSON parsing, XML parsing, and examples. I could not launch VS Code or Kate inside this environment, so the final editor-rendering check still needs to be done locally with the included examples.

* * *

**You:**

What sort of enforcement mechanisms exist that would help increase agent instruction following with this convention standard. Would something like hooks or a language server or an MCP server be options

* * *

**ChatGPT:**

Yes: **hooks, a language server, and an MCP server are all valid options**, but they enforce different things. The strongest design is a **layered enforcement stack** with a shared validator at the center.

My recommendation:

```
Pseudocode standard
        ↓
apseudo-lint CLI  ← single source of enforcement
        ↓
├─ pre-commit hook
├─ CI gate
├─ Claude/Codex lifecycle hooks
├─ VS Code language server diagnostics
└─ MCP tool/resource wrapper
```

The key is: **build one validator first**. Everything else should call that same validator. Do not put separate enforcement logic in VS Code, Kate, Claude hooks, Codex hooks, and MCP independently.

## Bottom line

| Mechanism | Enforcement strength | Best use |
| --- | --- | --- |
| **CLI validator/linter** | Very high | Source of truth for rules |
| **pre-commit hook** | High | Stops bad pseudocode before commit |
| **CI check** | Very high | Prevents merge/release drift |
| **Claude/Codex hooks** | High | Blocks or redirects agent behavior during the agent loop |
| **Language server** | Medium | Editor feedback, diagnostics, quick fixes |
| **MCP server** | Medium-high | Exposes validation, templates, canonical rules, and workflow tools to agents |
| **Syntax highlighting** | Low | Readability only |
| **Prompt instructions alone** | Low-medium | Necessary, but not sufficient |

## 1. Start with a real linter/validator

This is the enforcement core.

For your pseudocode convention, the validator should check things like:

```
- Every while loop has a cap, timeout, or explicit stop condition.
- Every process has declared inputs and outputs.
- Every branch has an action, transition, raise, continue, break, or return.
- Every loop mutates its loop condition or has an explicit external wait condition.
- Every process has at least one success outcome and one failure outcome.
- Known outcomes use approved names: Accepted, Blocked, NeedsUserDecision, etc.
- Normative terms follow the allowed vocabulary: MUST, SHOULD, MAY, MUST NOT.
- Function/action names use lower_snake_case.
- No TODO/FIXME appears in a normative block unless explicitly marked as unresolved.
```

The validator should be callable like this:

```Bash
apseudo-lint docs/**/*.md standards/**/*.apseudo
```

Output should be agent-friendly:

```
docs/process.md:42 APSEUDO-WHILE-001 while loop has no bounded stop condition
docs/process.md:57 APSEUDO-BRANCH-003 else branch does not end in action or return
docs/process.md:88 APSEUDO-OUTCOME-002 unknown outcome "Done"; use Accepted/Blocked/NeedsUserDecision
```

This is the layer that actually turns the convention from “guidance” into an enforceable standard.

## 2. Add pre-commit and CI

This is the most reliable enforcement for repositories. Codex’s own customization guidance explicitly recommends using custom instructions for conventions, then adding pre-commit hooks and linters to enforce those rules. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers](https://developers.openai.com/codex/concepts/customization?utm_source=chatgpt.com)

A pre-commit hook catches violations before they enter history:

```YAML
repos:
  - repo: local
    hooks:
      - id: apseudo-lint
        name: Validate Agent Pseudocode
        entry: uv run apseudo-lint
        language: system
        files: '\.(md|apseudo|agentpseudo)$'
```

CI catches anything that bypasses local hooks:

```YAML
name: pseudocode-standard

on:
  pull_request:
  push:
    branches: [main]

jobs:
  apseudo-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync
      - run: uv run apseudo-lint docs standards
```

This matters because agents can forget instructions, but they cannot merge through a failing required check unless the repo policy allows it.

## 3. Use agent hooks for runtime enforcement

Hooks are a good fit. They are stronger than instructions because they run deterministic scripts at lifecycle points.

Claude Code hooks can run code at key lifecycle points, including formatting after edits, blocking commands before execution, sending notifications, and injecting context at session start. [![](https://www.google.com/s2/favicons?domain=https://code.claude.com&sz=128)Claude](https://code.claude.com/docs/en/hooks-guide?utm_source=chatgpt.com) Claude’s hook reference covers events, configuration, JSON input/output formats, exit codes, async hooks, HTTP hooks, prompt hooks, and MCP tool hooks. [![](https://www.google.com/s2/favicons?domain=https://code.claude.com&sz=128)Claude](https://code.claude.com/docs/en/hooks?utm_source=chatgpt.com)

Codex also has hooks. OpenAI describes Codex hooks as an extensibility framework that runs deterministic scripts during the Codex lifecycle. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers](https://developers.openai.com/codex/hooks?utm_source=chatgpt.com)

Use hooks for things like:

```
SessionStart:
  Inject the pseudocode standard summary and validator command.

PostEdit / PostToolUse:
  If files matching *.md or *.apseudo changed, run apseudo-lint.

PreCommit / PreSubmit:
  Block if apseudo-lint fails.

PreCommand:
  Block commands that attempt to bypass validation, such as committing modified standards without checks.

Stop / FinalResponse:
  Require the agent to report validator status when pseudocode files changed.
```

The important part: the hook should not reason. It should run the validator.

Good hook behavior:

```
Changed files include docs/process.md
Running: uv run apseudo-lint docs/process.md
Violation found:
  APSEUDO-WHILE-001 line 42: while loop has no bounded stop condition
Blocking completion.
```

Bad hook behavior:

```
Ask the model to review whether the pseudocode seems okay.
```

That just moves the problem back into probabilistic compliance.

## 4. Add a language server for authoring feedback

A language server is useful, but I would not make it the primary enforcement mechanism.

LSP is designed to provide features such as diagnostics, completion, hover, code actions, and go-to-definition across editors. [![](https://www.google.com/s2/favicons?domain=https://microsoft.github.io&sz=128)Microsoft GitHub](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/?utm_source=chatgpt.com) VS Code’s language server guide describes language servers as a way to implement autocomplete, diagnostics, jump-to-definition, and related language features. [![](https://www.google.com/s2/favicons?domain=https://code.visualstudio.com&sz=128)Visual Studio Code](https://code.visualstudio.com/api/language-extensions/language-server-extension-guide?utm_source=chatgpt.com) VS Code diagnostics can be pushed from a language server using `textDocument/publishDiagnostics`. [![](https://www.google.com/s2/favicons?domain=https://code.visualstudio.com&sz=128)Visual Studio Code](https://code.visualstudio.com/api/language-extensions/programmatic-language-features?utm_source=chatgpt.com)

For your pseudocode standard, a language server could provide:

```
Diagnostics:
  - unbounded while loop
  - missing return path
  - unknown outcome name
  - unknown normative keyword

Hover:
  - show meaning of MUST / SHOULD / MAY
  - show allowed outcome definitions
  - show rule explanation for APSEUDO-WHILE-001

Completion:
  - Accepted(...)
  - Blocked(...)
  - NeedsUserDecision(...)
  - process ...:
  - while round <= max_rounds:

Code actions:
  - Add round cap
  - Add fallback else branch
  - Convert TODO to OpenIssue(...)
```

The language server should call the same `apseudo-lint` parser internally. That keeps editor diagnostics and CI results aligned.

Practical order:

```
Phase 1: CLI linter
Phase 2: pre-commit + CI
Phase 3: VS Code extension calls linter directly
Phase 4: LSP only if direct diagnostics become too limited
```

Do not start with LSP. It adds architecture before the rule set has stabilized.

## 5. Use MCP as an agent-facing control plane, not as the only gate

MCP is absolutely an option, but it is best for **capability exposure**, not hard enforcement by itself. The official MCP docs describe it as an open standard for connecting AI applications to external systems, including data sources, tools, and workflows. [![](https://www.google.com/s2/favicons?domain=https://modelcontextprotocol.io&sz=128)Model Context Protocol](https://modelcontextprotocol.io/docs/getting-started/intro?utm_source=chatgpt.com) MCP tools let servers expose callable tools with names, schemas, and metadata that models can invoke. [![](https://www.google.com/s2/favicons?domain=https://modelcontextprotocol.io&sz=128)Model Context Protocol](https://modelcontextprotocol.io/specification/2025-06-18/server/tools?utm_source=chatgpt.com)

For your convention, an MCP server could expose tools like:

```
apseudo.validate_file(path)
apseudo.validate_text(text)
apseudo.explain_rule(rule_id)
apseudo.render_mermaid(path)
apseudo.generate_template(process_type)
apseudo.repair_suggestion(path, rule_id)
apseudo.list_allowed_outcomes()
apseudo.get_standard_version()
```

That would help agents because they can ask the tool instead of guessing.

However, MCP is not enough as the enforcement boundary because the agent must choose to call the tool unless the host or hook forces it. Use MCP for **agent ergonomics** and hooks/CI for **hard enforcement**.

Good pattern:

```
Agent edits process.md
↓
Hook detects changed pseudocode file
↓
Hook calls apseudo-lint directly
↓
If invalid, hook blocks completion
↓
Agent may call MCP apseudo.explain_rule() to understand the failure
```

That is much stronger than:

```
Agent may call MCP validate_file() if it remembers.
```

## 6. Add repository instruction files, but treat them as reminders

Codex reads `AGENTS.md` files before doing work, and OpenAI’s docs describe layering global guidance with project-specific overrides for consistent expectations. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers](https://developers.openai.com/codex/guides/agents-md?utm_source=chatgpt.com) Codex best-practice guidance says the generated `AGENTS.md` should be edited to match how the team builds, tests, reviews, and ships code. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers](https://developers.openai.com/codex/learn/best-practices?utm_source=chatgpt.com)

For your repo, `AGENTS.md` / `CLAUDE.md` should say:

```Markdown
## Pseudocode standard

When editing `.apseudo`, `.agentpseudo`, or fenced `apseudo` blocks in Markdown:

- Follow `docs/standards/pythonic-pseudocode-standard.md`.
- Run `uv run apseudo-lint <changed-files>` before completion.
- Do not declare the task complete if `apseudo-lint` fails.
- If a rule appears wrong, surface the rule ID and rationale instead of bypassing it.
```

But this is still soft enforcement. The hard enforcement is hooks, pre-commit, and CI.

## 7. Enforcement levels I would define

Use levels so the agent knows what matters.

```
Level 0 — Readability
  Syntax highlighting, snippets, examples.

Level 1 — Authoring feedback
  VS Code diagnostics, Kate highlighting, optional LSP.

Level 2 — Local hard check
  CLI validator and pre-commit hook.

Level 3 — Agent runtime check
  Claude/Codex hooks run validator after edits and before completion.

Level 4 — Repository gate
  CI check required for PR merge.

Level 5 — Workflow gate
  Release/merge automation refuses to proceed unless validation passes.
```

For your use case, I would target **Level 3 minimum** and **Level 4 for standards repositories**.

## Concrete recommendation

Build these in this order:

```
1. apseudo-lint CLI
2. pytest fixture suite for valid/invalid examples
3. pre-commit hook
4. GitHub Actions CI check
5. Claude/Codex hooks that run apseudo-lint on changed files
6. VS Code diagnostics or LSP
7. MCP server wrapping the validator and standard metadata
```

The sequence matters. A language server without CI is advisory. An MCP server without hooks is optional. A hook without a shared validator becomes duplicated logic. A validator with pre-commit and CI is immediately useful.

## What I would enforce first

Start with the rules that directly prevent bad agent behavior:

```
APSEUDO-WHILE-001
Every while loop MUST include a bounded stop condition.

APSEUDO-FOR-001
Every for loop MUST iterate over a defined collection or bounded range.

APSEUDO-BRANCH-001
Every if/elif/else chain MUST include an explicit fallback unless the condition set is exhaustive.

APSEUDO-RETURN-001
Every process MUST terminate in an approved outcome.

APSEUDO-ACTION-001
Every mutating action MUST be followed by a verification action or explicit reason why verification is not required.

APSEUDO-ROUND-001
Every review/revision loop MUST increment or otherwise update its loop-control state.

APSEUDO-BLOCKER-001
Unresolved blockers MUST be carried forward or explicitly dismissed with rationale.

APSEUDO-NORM-001
Normative keywords MUST come from the approved vocabulary.
```

Those rules attack the actual failure modes: infinite loops, ambiguous branches, silent completion, skipped verification, and lossy blocker handling.

## Final answer

Yes, use all three — but not equally.

**Hooks are the best agent-runtime enforcement mechanism.**  
**A language server is the best authoring-feedback mechanism.**  
**An MCP server is the best agent-access mechanism for validators, templates, and rule explanations.**  
**The CLI validator plus pre-commit plus CI is the actual enforcement backbone.**

The architecture should be:

```
One validator.
Many integrations.
No duplicated policy logic.
```

* * *

**You:**

Create the linter/validator, pre-Commit and CI, and agent hooks

* * *

**ChatGPT:**

I’ll extend the syntax project into an enforcement bundle with a shared validator CLI, fixtures/tests, pre-commit, GitHub Actions CI, and Claude/Codex hook templates all using the same validator.

I found the existing bundle and will update it in place, replacing the future-linter note with a mostly-stdlib Python package. I’m checking current hook schemas before writing configs.

A validation issue surfaced: `lint.py` was truncated. I’m rebuilding that core, then rerunning pytest, ruff, and pyright before packaging.

Done. I created the enforcement bundle:

Expanded project folder:

What I added/updated:

| Area | Files |
| --- | --- |
| Validator/linter | `src/apseudo_lint/`, `scripts/apseudo-lint`, `.apseudo-lint.toml` |
| Tests/fixtures | `tests/test_linter.py`, `tests/fixtures/valid/*`, `tests/fixtures/invalid/*` |
| pre-commit | `.pre-commit-config.yaml`, `.pre-commit-hooks.yaml` |
| CI | `.github/workflows/apseudo-lint.yml` |
| Agent hooks | `.agent-hooks/apseudo-hook.py`, `.claude/settings.json`, `.codex/hooks.json` |
| Agent instructions | `AGENTS.md`, `CLAUDE.md` |
| Ops docs | `docs/ENFORCEMENT.md`, `docs/enforcement/ENFORCEMENT-GUIDE.md` |
| Install/smoke scripts | `scripts/install-enforcement.sh`, `scripts/run-enforcement-smoke-test.sh` |

The linter currently enforces structural rules including bounded `while` loops, explicit terminal outcomes, valid process declarations, fallback branches, approved outcome names, placeholder bodies, normative keyword casing, max nesting, and optional verification after mutating actions.

I validated the package with:

```Bash
scripts/run-enforcement-smoke-test.sh
```

That ran:

```Bash
uv sync --extra dev
uv run pytest
uv run apseudo-lint .
uv run ruff check src tests .agent-hooks
uv run pyright
python3 -m json.tool .claude/settings.json
python3 -m json.tool .codex/hooks.json
```

Result:

```
11 passed
apseudo-lint: checked 30 file(s); no diagnostics.
All checks passed.
0 errors, 0 warnings, 0 informations.
Enforcement smoke test passed.
```

The Claude hook config uses `SessionStart`, `PostToolUse`, and `Stop`; Claude’s hook reference documents these lifecycle events and says command hooks receive JSON context on stdin. It also shows PostToolUse matchers for file-edit tools such as `Edit|Write`. [![](https://www.google.com/s2/favicons?domain=https://code.claude.com&sz=128)Claude+1](https://code.claude.com/docs/en/hooks)

The Codex hook config uses project-local `.codex/hooks.json`; Codex docs say hooks can be discovered from `<repo>/.codex/hooks.json`, project-local hooks require trust, and `/hooks` is used to inspect/review/trust hook definitions. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers](https://developers.openai.com/codex/hooks) The Codex command examples also use git-root path resolution for repo-local hooks and note that commands run with the session `cwd`. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers](https://developers.openai.com/codex/hooks)

Fast local install after unzipping:

```Bash
cd agent-pseudocode-syntax
uv sync --extra dev
scripts/run-enforcement-smoke-test.sh
scripts/install-enforcement.sh
```

For hard repo enforcement, commit the files and make the GitHub Actions job named **Validate pseudocode standard** required in branch protection.

Caveat: I statically validated the hook configs and directly executed the shared hook script, but I could not launch Claude Code or Codex inside this sandbox. You will still need to review/trust the project hooks locally through each tool’s hook UI before relying on runtime enforcement.

* * *

**You:**

Now create the formatter, language server  and auto complete

* * *

**ChatGPT:**

I’ll extend the existing bundle with a shared formatter/parser core, CLI formatter, Python LSP, VS Code client integration, completions/snippets, tests, docs, and a fresh zip.

I found the existing package and grammar pipeline are clean, so I’m wiring the formatter and LSP into them. The LSP will be minimal Python without a pygls dependency.

Done. I extended the project to include the formatter, language server, and autocomplete layer.

Download the full updated bundle:

Expanded clean project folder:

Direct VS Code extension package:

What I added:

| Area | Files |
| --- | --- |
| Formatter | `src/apseudo_lint/formatting.py`, `src/apseudo_lint/format_cli.py`, `scripts/apseudo-format` |
| Language server | `src/apseudo_lint/lsp.py`, `scripts/apseudo-lsp` |
| Autocomplete/hover data | `src/apseudo_lint/completions.py` |
| VS Code LSP client | `vscode/extension.js`, updated `vscode/package.json` |
| VS Code snippets | `vscode/snippets/agent-pseudocode.code-snippets`, `vscode/snippets/markdown.code-snippets` |
| Kate LSP config | `kate/lsp-client-settings.json`, `kate/lsp-client-settings.markdown-opt-in.json` |
| Tests | `tests/test_formatter.py`, `tests/test_lsp_features.py`, `tests/test_lsp_server.py` |
| Docs | `docs/FORMATTER-LSP-AUTOCOMPLETE.md`, `docs/FORMATTER.md`, `docs/LANGUAGE-SERVER.md`, `docs/AUTOCOMPLETE.md`, updated install/editor docs |

The language server is a small dependency-free stdio LSP server. It implements diagnostics, completion, hover, and whole-document formatting using the same formatter and linter engines as the CLI tools. That matches the general LSP model of putting language intelligence in a server while editors act as clients. [![](https://www.google.com/s2/favicons?domain=https://microsoft.github.io&sz=128)Microsoft GitHub+1](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/?utm_source=chatgpt.com)

The VS Code side uses `vscode-languageclient`, which is the standard VS Code pattern for wiring an editor extension to a language server. [![](https://www.google.com/s2/favicons?domain=https://code.visualstudio.com&sz=128)Visual Studio Code](https://code.visualstudio.com/api/language-extensions/language-server-extension-guide?utm_source=chatgpt.com)

I validated the updated project with:

```Bash
uv run apseudo-format --check .
uv run apseudo-lint .
uv run pytest
uv run ruff check src tests .agent-hooks
uv run pyright
cd vscode && npm run check
scripts/run-enforcement-smoke-test.sh
unzip -t /mnt/data/agent-pseudocode-syntax-complete.zip
```

Result:

```
28 passed
apseudo-format: checked 34 file(s); no changes.
apseudo-lint: checked 34 file(s); no diagnostics.
All checks passed.
0 errors, 0 warnings, 0 informations.
Enforcement smoke test passed.
No errors detected in compressed data.
```

One caveat: I validated the server, formatter, VS Code extension manifest, grammar build, JSON, XML, tests, and packaged VSIX statically in the container. I could not launch VS Code or Kate interactively here, so the final runtime check is still opening the extension locally and confirming the LSP starts in the editor output panel.

* * *

**You:**

Next do an analysis on what features are missing for the standard including anything we haven’t already made, but you mentioned above. Consider each individual individually are there additional features you could add to the language server or the hooks etc.  Create all features that you know and find. Ensure that the features work for both Claude code and codex cli. Include a document with all of the agent instruction wording that I should put into the repositories.  And then finally review the entire project starting with the language convention itself to verify that it is complete, and then that it is properly represented throughout all all tooling.

* * *

**ChatGPT:**

I’ll audit the standard and existing tooling as one baseline, then add practical missing enforcement, editor, and agent-facing features without duplicating policy logic. I’ll validate the result, package a new complete bundle, and include repository instruction wording plus an implementation/review report.

The main gaps are an MCP wrapper, richer LSP features, Claude/Codex skill support, stronger commit/push hooks, and repo-ready instruction templates. I’m wiring them through the existing shared core.

Done. I created the expanded, reviewed 0.4.0 bundle with the missing enforcement, agent-access, editor-repair, and review layers added.

Expanded project folder:

## What I added

| Area | Added |
| --- | --- |
| MCP server | `src/apseudo_lint/mcp.py`, `scripts/apseudo-mcp`, `.mcp.json`, `.codex/config.toml`, `docs/MCP.md` |
| Project review | `src/apseudo_lint/review.py`, `scripts/apseudo-review`, `docs/PROJECT-REVIEW-RESULT.md` |
| Rule catalog | `src/apseudo_lint/rules.py`, `docs/RULES.md`, `scripts/apseudo-explain` |
| Templates | `src/apseudo_lint/templates.py`, `scripts/apseudo-template` |
| Mermaid view | `src/apseudo_lint/mermaid.py`, `scripts/apseudo-mermaid` |
| Language server features | Code actions, document symbols, folding ranges, definition, references, workspace symbols |
| VS Code commands | Explain rule, review project, richer LSP-backed features |
| Claude Code support | Expanded `.claude/settings.json`, `.claude/skills/agent-pseudocode/SKILL.md` |
| Codex support | Expanded `.codex/hooks.json`, `.agents/skills/agent-pseudocode/SKILL.md`, `.codex/config.toml` |
| Agent hooks | Prompt, pre-tool, permission, post-tool, subagent, and stop hooks |
| Bypass protection | Blocks obvious enforcement bypasses like `git commit --no-verify`, `SKIP=...`, `pre-commit uninstall`, and edits to enforcement config |
| Agent wording | `docs/AGENT-INSTRUCTIONS-WORDING.md` with copy/paste blocks for repos |
| Analysis/review docs | `docs/FEATURE-GAP-ANALYSIS.md`, `docs/PROJECT-TRACEABILITY-REVIEW.md`, `docs/PROJECT-REVIEW-RESULT.md` |

The MCP server is stdio-based and writes only JSON-RPC messages to stdout, matching MCP’s stdio transport rules. MCP is now used as the agent-access layer, while hooks/pre-commit/CI remain the hard gates. [![](https://www.google.com/s2/favicons?domain=https://modelcontextprotocol.io&sz=128)Model Context Protocol+2![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers+2](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)

The Claude and Codex hook setups now cover the lifecycle points that matter for enforcement: session start, user prompt submission, pre-tool/permission checks, post-tool validation, subagent completion, and final stop checks. Claude Code documents hooks as lifecycle commands that receive JSON on stdin, and Codex documents project hook discovery plus common stdin fields for hook commands. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers+3![](https://www.google.com/s2/favicons?domain=https://code.claude.com&sz=128)Claude+3![](https://www.google.com/s2/favicons?domain=https://code.claude.com&sz=128)Claude+3](https://code.claude.com/docs/en/hooks)

The skill folders follow the current Claude Code and Codex skill layouts: Claude uses `.claude/skills/<skill>/SKILL.md`, while Codex reads repo skills from `.agents/skills` up to the repo root. [![](https://www.google.com/s2/favicons?domain=https://docs.anthropic.com&sz=128)Claude Platform Docs+1](https://docs.anthropic.com/en/docs/claude-code/skills)

The language server now exposes more of the standard LSP authoring surface: diagnostics, completion, hover, formatting, code actions, symbols, folding, definition, references, and workspace symbols. That aligns with the LSP model for editor language features and VS Code’s language-server extension pattern. [![](https://www.google.com/s2/favicons?domain=https://microsoft.github.io&sz=128)Microsoft GitHub+1](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/)

## Final project review result

The included `apseudo-review` result reports:

```
Files checked: 46
Diagnostics: 0 total, 0 error(s), 0 warning(s)
Completeness checks: all OK
```

## Validation performed

I ran:

```Bash
uv sync --extra dev
uv run pytest
uv run apseudo-format --check .
uv run apseudo-lint .
uv run apseudo-review .
uv run ruff check src tests .agent-hooks
uv run pyright
scripts/run-enforcement-smoke-test.sh
cd vscode && npm install && npm run check && npm run package
unzip -t /mnt/data/agent-pseudocode-syntax-verified.zip
```

Results:

```
35 passed
apseudo-format: checked 46 file(s); no changes.
apseudo-lint: checked 46 file(s); no diagnostics.
All checks passed.
0 errors, 0 warnings, 0 informations.
Enforcement smoke test passed.
VSIX packaged: agent-pseudocode-0.4.0.vsix
ZIP integrity check passed.
```

## Important caveat

I validated the code, tests, JSON/TOML configs, generated grammars, packaged VSIX, hook script behavior, MCP protocol smoke test, and project review in the container. I could not launch Claude Code, Codex CLI, VS Code, or Kate interactively here, so you still need to trust/enable the project hooks and confirm MCP/skills are visible inside those tools locally.

* * *

**You:**

Help me understand how it’s best to use this. Please give me usage examples of when I would use one of the pseudo or agent pseudo scripts. How does it get involved? How is it fed to the agent?

* * *

**ChatGPT:**

The easiest mental model: the pseudocode files are not “scripts you execute.” They are deterministic instruction artifacts that agents read, validate, and follow like a process spec.

The best way to use this is to treat `.apseudo` / fenced `apseudo` blocks as **agent-readable process contracts**.

They are not normal scripts. They are closer to:

> “Here is the exact workflow, branching logic, loop limits, stop conditions, and allowed outcomes the agent must follow.”

The tooling then makes those contracts more reliable by highlighting, linting, formatting, validating, and feeding them to Claude Code or Codex.

## 1. What is an `.apseudo` file for?

Use an `.apseudo` file when the instruction is:

* procedural
* repeatable
* branch-heavy
* safety-sensitive
* likely to be reused across repos
* easy for agents to misunderstand in prose

Good candidates:

```
review-loop.apseudo
release-gate.apseudo
issue-triage.apseudo
upstream-bug-report.apseudo
handoff-size-control.apseudo
spec-amendment-loop.apseudo
template-repo-sync.apseudo
```

Bad candidates:

```
vision-statement.apseudo
project-background.apseudo
general-style-preferences.apseudo
brainstorming-notes.apseudo
```

Use prose for intent and context. Use pseudocode for **control flow**.

## 2. Three ways it gets involved

There are three practical usage modes.

### Mode A — embedded in Markdown standards

This is probably your default.

Example:

````Markdown
# GitHub Issue Handling Standard

## Process

```apseudo
process handle_upstream_bug(observed_bug, source_repo, upstream_repo):
    if upstream_repo is None:
        return Blocked(reason="upstream repository is unknown")

    if source_repo == upstream_repo:
        create_issue(repo=source_repo, type="bug", evidence=observed_bug)
        return Accepted(reason="local issue created")

    issue = create_issue(
        repo=upstream_repo,
        type="bug",
        evidence=observed_bug,
        references=[source_repo],
    )

    create_tracking_issue(
        repo=source_repo,
        upstream_issue=issue,
        status="blocked_by_upstream",
    )

    return Accepted(reason="upstream and tracking issues created")
```
````

How it gets fed to the agent:

* The agent reads the Markdown standard through normal repo context.
* `AGENTS.md` / `CLAUDE.md` tells the agent that fenced `apseudo` blocks are normative.
* The hooks/linter validate the block when the file is edited.
* The MCP server can explain or validate the block on demand.

This is the best mode for standards documents.

### Mode B — standalone `.apseudo` files

Use this when a process is reusable enough to deserve its own artifact.

Example:

```
standards/processes/release-gate.apseudo
standards/processes/spec-review-loop.apseudo
standards/processes/agent-handoff-size.apseudo
```

Example file:

```Python
process release_gate(change_set, ci_result, user_approval_required):
    if ci_result.status != "passed":
        return Blocked(reason="CI did not pass")

    if change_set.includes_release_artifact:
        user_decision = ask_user_inline(
            question="Approve release?",
            options=["approve", "reject"],
        )

        if user_decision == "approve":
            publish_release(change_set)
            return Accepted(reason="release approved and published")

        else:
            return NeedsUserDecision(reason="release rejected or deferred")

    merge_change_set(change_set)
    return Accepted(reason="non-release change merged")
```

How it gets fed to the agent:

* `AGENTS.md` or `CLAUDE.md` points to the file.
* Your prompt says: “Follow `standards/processes/release-gate.apseudo`.”
* Hooks/linter ensure the file remains valid.
* MCP gives the agent a structured way to validate/explain/render it.

This is the best mode for reusable workflows.

### Mode C — prompt-local pseudocode

Use this when you are giving one-off instructions to an agent.

Example prompt:

````Markdown
Follow this process exactly:

```apseudo
process fix_lint_failure(failure_output):
    if failure_output is empty:
        run_linter()
        failure_output = collect_linter_output()

    for diagnostic in failure_output.diagnostics:
        fix_diagnostic(diagnostic)
        run_targeted_check(diagnostic.file)

        if targeted_check_failed:
            return Blocked(reason="targeted check still fails", evidence=targeted_check_output)

    run_full_linter()

    if full_linter_passed:
        return Accepted(reason="lint failures fixed")

    return Blocked(reason="full linter still fails", evidence=full_linter_output)
```
````

How it gets fed to the agent:

* It is directly in the prompt.
* No file lookup is needed.
* If the agent writes it into a repo file, the linter/hook system starts enforcing it.

This is useful for ad hoc work, but less durable than Mode A or B.

## 3. How the agent actually sees it

There are several channels.

### Channel 1 — normal repo context

Claude Code and Codex both operate over repository files. Codex uses `AGENTS.md` for reusable project guidance; OpenAI’s docs describe `AGENTS.md` as the file Codex reads before doing work. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers](https://developers.openai.com/codex/guides/agents-md?utm_source=chatgpt.com) Claude Code similarly supports repo/project instruction files such as `CLAUDE.md`, plus hooks and skills. [![](https://www.google.com/s2/favicons?domain=https://docs.anthropic.com&sz=128)Claude Platform Docs](https://docs.anthropic.com/en/docs/claude-code/overview?utm_source=chatgpt.com)

So the normal pattern is:

```
repo/
├── AGENTS.md
├── CLAUDE.md
├── standards/
│   ├── pythonic-pseudocode-standard.md
│   └── processes/
│       ├── review-loop.apseudo
│       ├── release-gate.apseudo
│       └── issue-triage.apseudo
```

Then your task prompt can be short:

```
Implement the new release workflow. Follow standards/processes/release-gate.apseudo and do not mark complete unless apseudo-lint passes.
```

The pseudocode is “fed” through the repo files plus the instruction file.

### Channel 2 — `AGENTS.md` / `CLAUDE.md`

This is where you tell the agent **what the pseudocode means**.

Example wording:

````Markdown
## Agent pseudocode

Files ending in `.apseudo` and Markdown fenced blocks labeled `apseudo` or `agent-pseudocode` are normative process instructions.

When a task references one of these files or blocks, follow it as the control-flow source of truth. Treat prose as explanatory context unless it conflicts with the pseudocode. If prose and pseudocode conflict, stop and surface the conflict.

Before completing work that creates or edits pseudocode, run:

```bash
uv run apseudo-format --check .
uv run apseudo-lint .
uv run apseudo-review .
````

Do not bypass hooks, pre-commit, or CI enforcement.

````

That is the “agent contract.”

### Channel 3 — hooks

Hooks are automatic enforcement. Claude Code documents hooks as user-defined commands that run at lifecycle points, and Codex has project-local hooks that can be reviewed/trusted through `/hooks`. :contentReference[oaicite:2]{index=2}

The hook path is:

```text
agent edits .apseudo or Markdown
        ↓
PostToolUse / post-edit hook fires
        ↓
apseudo-lint runs
        ↓
failure blocks or warns
        ↓
agent must fix before completion
````

This is how pseudocode stops being “just another instruction.”

### Channel 4 — MCP server

MCP is not the hard gate. It is the agent-facing tool layer.

The agent can call tools like:

```
apseudo.validate_file
apseudo.explain_rule
apseudo.generate_template
apseudo.render_mermaid
apseudo.review_project
```

So instead of guessing why a rule failed, the agent can ask the MCP server.

Use MCP for:

* validation on demand
* rule explanations
* template generation
* rendering Mermaid from process flow
* project-wide review

Use hooks/CI for hard enforcement.

### Channel 5 — language server

The language server feeds feedback to you while editing:

* diagnostics
* completions
* hovers
* code actions
* formatting
* symbols
* folding

This helps you author better pseudocode before the agent ever sees it.

## 4. Example: when to use `.apseudo` vs Markdown prose

### Use prose for intent

```Markdown
The release gate prevents an agent from publishing or merging release-impacting changes without explicit inline user approval. It also prevents the agent from using GitHub UI approval as a substitute for conversational approval.
```

### Use pseudocode for procedure

```Python
process release_gate(change_set, ci_result):
    if ci_result.status != "passed":
        return Blocked(reason="CI failed")

    if change_set.requires_release:
        approval = ask_user_inline("Approve release?")

        if approval != "approve":
            return NeedsUserDecision(reason="release not approved")

    perform_release(change_set)
    return Accepted(reason="release completed")
```

### Use rules for invariants

```Markdown
- The agent MUST NOT publish a release without explicit inline approval.
- The agent MUST NOT require the user to approve through GitHub UI.
- The agent MUST stop if CI status is missing or failed.
```

That three-part structure is the cleanest.

## 5. Concrete usage examples

### Example 1 — agent handoff size control

Use when agents keep guessing document sizes.

```Python
process prepare_handoff(document, max_chars):
    measured_chars = count_chars(document)

    if measured_chars <= max_chars:
        return Accepted(reason="handoff within size limit")

    while measured_chars > max_chars and revision_round <= 3:
        excess_chars = measured_chars - max_chars
        target_reduction = excess_chars + safety_margin_chars

        document = reduce_document(
            document,
            target_reduction=target_reduction,
            preserve_required_sections=True,
        )

        measured_chars = count_chars(document)
        revision_round += 1

    if measured_chars <= max_chars:
        return Accepted(reason="handoff reduced within size limit")

    return Blocked(
        reason="handoff still exceeds limit",
        measured_chars=measured_chars,
        max_chars=max_chars,
    )
```

Use this in:

```
standards/processes/handoff-size-control.apseudo
```

Then prompt:

```
Before producing the handoff, follow standards/processes/handoff-size-control.apseudo. Measure first; do not guess reductions.
```

### Example 2 — review amendment loop

Use when Claude and Codex need bounded review loops.

```Python
process amend_spec(spec, reviewer, max_rounds=5):
    blockers = []

    for round in range(1, max_rounds + 1):
        review = reviewer.review(spec)

        if review.status == "approved":
            mark_final(spec)
            return Accepted(reason="spec approved")

        if review.blockers:
            blockers = review.blockers
            spec = revise_spec(spec, blockers)
            continue

        return Blocked(reason="review status ambiguous")

    return Blocked(
        reason="round cap reached",
        unresolved_blockers=blockers,
    )
```

Use this in:

```
standards/processes/spec-amendment-loop.apseudo
```

Prompt:

```
Run the spec amendment process using standards/processes/spec-amendment-loop.apseudo. Stop after the round cap and surface blockers instead of continuing.
```

### Example 3 — upstream bug issue handling

Use when repo A depends on repo B and the agent finds a bug in B.

```Python
process report_upstream_bug(source_repo, upstream_repo, bug_evidence):
    if upstream_repo is None:
        return Blocked(reason="upstream repository is unknown")

    upstream_issue = create_issue(
        repo=upstream_repo,
        title=derive_bug_title(bug_evidence),
        body=include_reproduction_steps(bug_evidence),
    )

    tracking_issue = create_issue(
        repo=source_repo,
        title="Track upstream bug",
        body=link_to(upstream_issue),
    )

    return Accepted(
        reason="upstream bug and local tracking issue created",
        artifacts=[upstream_issue, tracking_issue],
    )
```

Prompt:

```
If you discover a bug in a repo dependency that is also in my GitHub inventory, follow standards/processes/report-upstream-bug.apseudo.
```

### Example 4 — template repository sync

Use when a standards release should update a template repo.

```Python
process sync_template_repo(standard_release, template_repo):
    if standard_release.status != "published":
        return Blocked(reason="standard release is not published")

    changes = compute_template_delta(
        source=standard_release.artifacts,
        target=template_repo,
    )

    if changes.empty:
        return Accepted(reason="template already matches standard release")

    apply_changes(template_repo, changes)
    run_template_validation(template_repo)

    if validation_failed:
        return Blocked(reason="template validation failed")

    open_pull_request(
        repo=template_repo,
        title="Sync template with standard release",
        body=summarize_changes(changes),
    )

    return Accepted(reason="template sync PR opened")
```

This is ideal as a standalone `.apseudo` file because it is reusable automation logic.

## 6. How it should be installed into each repo

In a normal project repo, you do **not** necessarily need to copy the entire source project. You need the consumer pieces.

Minimum repo integration:

```
repo/
├── AGENTS.md
├── CLAUDE.md
├── .pre-commit-config.yaml
├── .github/workflows/apseudo-lint.yml
├── .claude/settings.json
├── .codex/hooks.json
├── .mcp.json
├── standards/
│   ├── pythonic-pseudocode-standard.md
│   └── processes/
│       └── *.apseudo
└── pyproject.toml
```

Best repo integration if this becomes a real internal standard:

```
repo/
├── AGENTS.md
├── CLAUDE.md
├── standards/
│   └── processes/*.apseudo
└── dependency on apseudo-lint package
```

Then the tooling package is installed as a dev dependency instead of copied everywhere.

## 7. How you personally would use it day to day

### Scenario: writing a new process standard

You create:

```Bash
standards/processes/review-loop.apseudo
```

You write the process using Pythonic pseudocode.

Then run:

```Bash
uv run apseudo-format standards/processes/review-loop.apseudo
uv run apseudo-lint standards/processes/review-loop.apseudo
uv run apseudo-mermaid standards/processes/review-loop.apseudo
```

Then tell the agent:

```
Use standards/processes/review-loop.apseudo as the control-flow source of truth. Update implementation docs to reference it, but do not duplicate the logic in prose.
```

### Scenario: asking Claude Code or Codex to implement a workflow

Prompt:

```
Implement the GitHub upstream bug reporting workflow. The normative process is standards/processes/report-upstream-bug.apseudo. Do not infer alternate behavior from prose. If the pseudocode conflicts with existing docs, stop and surface the conflict.
```

The agent reads the file, follows it, and the hooks/linter catch edits that break it.

### Scenario: agent edits a process file

Agent modifies:

```
standards/processes/spec-amendment-loop.apseudo
```

Hook fires:

```
apseudo-format --check changed-file
apseudo-lint changed-file
apseudo-review .
```

If the agent accidentally writes:

```Python
while review.status != "approved":
    revise_spec()
```

The linter should flag it as an unbounded loop.

The agent then fixes it:

```Python
for round in range(1, max_rounds + 1):
    ...
```

## 8. What not to do

Do not use `.apseudo` as a general notes format.

Bad:

```Python
process thoughts_about_repo():
    maybe use github issues
    maybe update template
    think about branch protection
```

That should be prose.

Do not encode everything as pseudocode. Pseudocode is for **behavior**.

Do not duplicate the same workflow in five places. Put the workflow in one `.apseudo` file and reference it.

Do not rely on syntax highlighting as enforcement. Highlighting helps you read; linter/hooks/CI enforce.

## 9. Best repository wording

Put this in `AGENTS.md` and `CLAUDE.md`:

````Markdown
## Agent pseudocode standard

This repository uses Pythonic agent pseudocode as a normative process-instruction format.

Treat files ending in `.apseudo` or `.agentpseudo`, and Markdown fenced blocks labeled `apseudo` or `agent-pseudocode`, as control-flow source-of-truth artifacts.

When a task references an agent pseudocode file or block:

- Follow the pseudocode over nearby explanatory prose.
- Preserve explicit loop bounds, stop conditions, guards, and terminal outcomes.
- Do not convert bounded loops into unbounded loops.
- Do not remove fallback branches or failure outcomes.
- If the pseudocode conflicts with prose, existing implementation, or another standard, stop and surface the conflict.

Before completing work that creates or edits pseudocode, run:

```bash
uv run apseudo-format --check .
uv run apseudo-lint .
uv run apseudo-review .
````

If validation fails, fix the pseudocode or report the blocker. Do not bypass hooks, pre-commit, CI, or validation checks.

````

That is the agent-facing bridge between the language convention and actual behavior.

## Bottom line

Use `.apseudo` when you want to give the agent a **bounded, checkable workflow**.

It gets involved through:

```text
repo files
+ AGENTS.md / CLAUDE.md
+ hooks
+ linter / formatter
+ CI
+ MCP
+ language server
````

The agent is fed the pseudocode either directly in your prompt, through referenced repo files, or through standards documents. The enforcement stack then makes sure the pseudocode itself stays structurally valid and that the agent does not silently break or bypass it.

* * *

**You:**

Would it be possible to call this like you would call a bash script or Python script that’s in $PATH ?  I’m thinking that you would be able to put a shebang like character in a script that’s written in pseudocode.  When you call it at the command line using a flag – – Claude or – – Codex it would then feed that pseudo code into a headless Codex or Claude and perform whatever action that script is for.

* * *

**ChatGPT:**

Yes, this is feasible; I’ll treat it as a safe runner design, grounded in Unix shebang behavior and current Claude/Codex non-interactive invocation surfaces.

Yes. The right design is an **agent-backed pseudocode runner**:

```
executable .apseudo file
        ↓
apseudo-run wrapper from $PATH
        ↓
validate + format-check + render agent prompt
        ↓
launch headless Claude Code or Codex CLI
        ↓
agent performs the task in the selected workspace
        ↓
runner validates/report/parses final outcome
```

The pseudocode would not execute like Python bytecode or Bash commands. It would be **compiled into a constrained agent prompt** and sent to a headless agent.

Claude Code supports non-interactive/headless runs with `claude -p` / `--print`, including structured output and options such as `--allowedTools`, `--output-format`, `--max-turns`, and `--max-budget-usd`. It also has a `--bare` mode for scripted runs, but `--bare` skips normal project discovery such as hooks, skills, MCP servers, and `CLAUDE.md`, so the runner would need to choose between “use project context” and “hermetic run.” [![](https://www.google.com/s2/favicons?domain=https://code.claude.com&sz=128)Claude+1](https://code.claude.com/docs/en/headless)

Codex CLI supports this pattern through `codex exec`, which OpenAI documents for scripted or CI-style runs that finish without human interaction. It accepts a prompt string or `-` to read from stdin, and supports options such as `--cd`, `--sandbox`, `--json`, `--output-last-message`, and `--output-schema`. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers](https://developers.openai.com/codex/cli/reference)

## The script form

I would make the executable file look like this:

```Python
#!/usr/bin/env apseudo-run
---
name: fix_ruff_failures
description: Fix Ruff failures in a bounded, verified loop.
default_agent: codex
mode: apply
workspace: git_root
requires_clean_git: false

claude:
  bare: false
  allowed_tools:
    - Read
    - Edit
    - Bash
  output_format: json
  max_turns: 8
  max_budget_usd: 2.00

codex:
  sandbox: workspace-write
  json: true
  output_schema: .apseudo/outcome.schema.json
---

process fix_ruff_failures(target="."):
    diagnostics = run_command("uv run ruff check {target}")

    if diagnostics.empty:
        return Accepted(reason="ruff already passes")

    for diagnostic in diagnostics:
        fix_diagnostic(diagnostic)
        targeted_result = run_command("uv run ruff check {diagnostic.file}")

        if targeted_result.failed:
            return Blocked(
                reason="targeted Ruff check still fails",
                evidence=targeted_result.output,
            )

    final_result = run_command("uv run ruff check {target}")

    if final_result.passed:
        return Accepted(reason="all Ruff failures fixed")

    return Blocked(
        reason="full Ruff check still fails",
        evidence=final_result.output,
    )
```

Then:

```Bash
chmod +x ./scripts/fix-ruff.apseudo
./scripts/fix-ruff.apseudo --codex -- target=src
./scripts/fix-ruff.apseudo --claude -- target=src
```

Or, if the file is installed somewhere in `$PATH`:

```Bash
fix-ruff --codex -- target=src
fix-ruff --claude -- target=src
```

The extension does not matter to the shell. The executable bit and the shebang matter.

## Why the shebang should stay simple

Use this:

```Bash
#!/usr/bin/env apseudo-run
```

Avoid this as the primary design:

```Bash
#!/usr/bin/env -S apseudo-run --codex --apply
```

Multi-argument shebangs are less portable and harder to debug. Put defaults in frontmatter, then allow command-line overrides:

```Bash
./fix-ruff.apseudo --claude
./fix-ruff.apseudo --codex
./fix-ruff.apseudo --agent claude
./fix-ruff.apseudo --agent codex
```

That gives you the same ergonomics without tying behavior to shell portability quirks.

## What `apseudo-run` would actually do

The runner should be a normal Python CLI installed into `$PATH`.

Conceptually:

```
apseudo-run receives:
  script path
  runner flags
  script arguments
        ↓
parse shebang-aware frontmatter
        ↓
extract pseudocode body
        ↓
validate with apseudo-lint
        ↓
optionally format-check with apseudo-format
        ↓
resolve workspace / git root
        ↓
render a provider-neutral execution prompt
        ↓
call Claude Code or Codex CLI
        ↓
parse structured result
        ↓
write logs
        ↓
return shell exit code
```

It should have two call styles:

```Bash
# Direct runner invocation
apseudo-run --codex ./scripts/fix-ruff.apseudo -- target=src

# Shebang invocation
./scripts/fix-ruff.apseudo --codex -- target=src
```

## How it feeds the agent

The runner would render a prompt like this internally:

````Markdown
You are executing an Agent Pseudocode script.

Script:
- name: fix_ruff_failures
- selected_agent: codex
- mode: apply
- workspace: /home/chris/project
- invocation_args:
  - target: src

Execution contract:
- Treat the pseudocode as the control-flow source of truth.
- Do not skip loop bounds, guards, fallback branches, or terminal outcomes.
- Use only approved terminal outcomes:
  - Accepted
  - Blocked
  - NeedsUserDecision
- If the pseudocode conflicts with repository instructions, stop and report the conflict.
- Before returning Accepted, run the verification steps specified by the pseudocode.
- Return final output matching the supplied JSON schema.

Pseudocode:

```apseudo
process fix_ruff_failures(target="."):
    ...
````

````

Then the provider adapter launches the selected tool.

For Claude Code, the command would be roughly:

```bash
claude -p \
  --output-format json \
  --max-turns 8 \
  --max-budget-usd 2.00 \
  --allowedTools "Read,Edit,Bash" \
  "$RENDERED_PROMPT"
````

For Codex CLI, the command would be roughly:

```Bash
printf '%s' "$RENDERED_PROMPT" | codex exec \
  --cd "$WORKSPACE" \
  --sandbox workspace-write \
  --json \
  --output-schema .apseudo/outcome.schema.json \
  -
```

Codex’s `codex exec` explicitly supports `-` for reading the prompt from stdin, and supports `--output-schema` for a JSON Schema file describing the expected final response shape. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers](https://developers.openai.com/codex/cli/reference) Claude Code supports JSON output and JSON-schema-shaped structured output in print mode. [![](https://www.google.com/s2/favicons?domain=https://code.claude.com&sz=128)Claude+1](https://code.claude.com/docs/en/headless)

## The output schema

The runner should require the agent to end with a machine-readable result:

```JSON
{
  "type": "object",
  "properties": {
    "outcome": {
      "type": "string",
      "enum": ["Accepted", "Blocked", "NeedsUserDecision"]
    },
    "reason": {
      "type": "string"
    },
    "summary": {
      "type": "string"
    },
    "artifacts": {
      "type": "array",
      "items": { "type": "string" }
    },
    "checks_run": {
      "type": "array",
      "items": { "type": "string" }
    },
    "evidence": {
      "type": "string"
    }
  },
  "required": ["outcome", "reason", "summary", "checks_run"]
}
```

Then map outcomes to exit codes:

```
0   Accepted
10  NeedsUserDecision
20  Blocked
30  pseudocode validation failed
31  runner config invalid
40  agent command failed
41  structured output invalid
50  safety policy blocked execution
```

This matters because then `.apseudo` scripts become composable:

```Bash
fix-ruff --codex -- target=src && run-tests --codex -- target=tests
```

## Agent selection

I would support all of these:

```Bash
script.apseudo --claude
script.apseudo --codex
script.apseudo --agent claude
script.apseudo --agent codex
APSEUDO_AGENT=claude script.apseudo
APSEUDO_AGENT=codex script.apseudo
```

Resolution order:

```
1. Explicit CLI flag
2. APSEUDO_AGENT environment variable
3. Frontmatter default_agent
4. Project config
5. Fail with NeedsUserDecision / configuration error
```

Use lowercase `--claude` and `--codex`; uppercase flag names are unusual for CLI tools.

## Modes

This should not default to “go edit my repo.”

Use explicit execution modes:

```Bash
script.apseudo --plan
script.apseudo --review
script.apseudo --apply
script.apseudo --dry-run
```

Suggested mapping:

| Mode | Claude Code | Codex CLI | Intended behavior |
| --- | --- | --- | --- |
| `plan` | `--permission-mode plan` | `--sandbox read-only` | inspect and propose only |
| `review` | read-oriented tools | `--sandbox read-only` | analyze/report |
| `apply` | edit/bash tools allowed | `--sandbox workspace-write` | modify workspace |
| `danger` | explicit only | `danger-full-access` or bypass flags | isolated runner only |

Codex documents `--dangerously-bypass-approvals-and-sandbox` / `--yolo` as bypassing approval prompts and sandboxing, and labels it dangerous; I would not let `.apseudo` frontmatter silently enable that. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers](https://developers.openai.com/codex/cli/reference)

## Hooks and MCP still matter

This runner does not replace hooks, MCP, or CI.

It adds a new entry point:

```
human calls script
        ↓
script launches headless agent
        ↓
agent edits repo
        ↓
hooks/linter/CI still enforce standards
```

Claude Code hooks are deterministic lifecycle commands, and Anthropic describes them as a way to ensure actions happen automatically rather than relying on the model to choose them. [![](https://www.google.com/s2/favicons?domain=https://code.claude.com&sz=128)Claude](https://code.claude.com/docs/en/hooks-guide?utm_source=chatgpt.com) Codex project-local hooks require the project `.codex/` layer to be trusted before they load. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers](https://developers.openai.com/codex/hooks?utm_source=chatgpt.com)

So the runner should have a config option:

```YAML
claude:
  bare: false
  use_project_hooks: true

codex:
  require_project_hooks_trusted: true
```

For Claude:

* Use normal `claude -p` when you want `CLAUDE.md`, hooks, MCP, skills, and project context.
* Use `claude --bare -p` only when you want hermetic scripted behavior and will pass every required setting explicitly.

Claude’s docs say bare mode skips auto-discovery of hooks, skills, plugins, MCP servers, auto memory, and `CLAUDE.md`; it is useful for CI/scripts where you want the same result on every machine. [![](https://www.google.com/s2/favicons?domain=https://code.claude.com&sz=128)Claude](https://code.claude.com/docs/en/headless)

## What this feature should be called

I would call it:

```
apseudo-run
```

Supporting aliases:

```
apseudo-claude
apseudo-codex
```

Examples:

```Bash
apseudo-run --codex ./scripts/fix-ruff.apseudo -- target=src
apseudo-run --claude ./scripts/review-spec.apseudo -- spec=docs/spec.md
apseudo-codex ./scripts/fix-tests.apseudo -- test_path=tests/test_api.py
apseudo-claude ./scripts/refactor-module.apseudo -- module=src/app/auth.py
```

## What would need to be added to the project

This would be a new layer on top of what already exists.

Add:

```
src/apseudo_lint/runner.py
src/apseudo_lint/runner_config.py
src/apseudo_lint/prompt_renderer.py
src/apseudo_lint/agent_adapters/
├── __init__.py
├── claude.py
└── codex.py
src/apseudo_lint/outcome.py
scripts/apseudo-run
scripts/apseudo-claude
scripts/apseudo-codex
docs/RUNNER.md
docs/EXECUTABLE-PSEUDOCODE.md
tests/test_runner_config.py
tests/test_prompt_renderer.py
tests/test_claude_adapter.py
tests/test_codex_adapter.py
tests/test_runner_exit_codes.py
```

The linter and formatter would also need to become **shebang/frontmatter-aware**, so this becomes valid:

```Python
#!/usr/bin/env apseudo-run
---
name: example
default_agent: codex
---

process example():
    return Accepted(reason="ok")
```

Right now the cleanest pseudocode format starts directly with `process`. Executable pseudocode needs metadata before the process body.

## When this is a good idea

Use executable `.apseudo` scripts for workflows that are:

```
- repeatable
- agentic
- bounded
- repository-aware
- not fully deterministic
- useful from the command line
```

Good examples:

```
fix-ruff
fix-pyright
review-spec
amend-spec
sync-template-repo
triage-github-issue
create-upstream-bug-report
generate-release-notes
repair-docs-links
review-agent-instructions
```

Bad examples:

```
backup-database
rotate-secrets
delete-old-files
deploy-production
rewrite-git-history
```

For deterministic or dangerous operations, Bash/Python should remain the executor. The `.apseudo` runner is best when the task requires judgment, repo inspection, edits, and verification.

## Best mental model

This would be like a **Make target backed by an AI agent**:

```Bash
make fix-ruff
```

becomes:

```Bash
fix-ruff --codex
```

But the “recipe” is not shell commands. The recipe is a validated pseudocode process that the agent must follow.

## Recommended first version

The first implementation should be intentionally conservative:

```
apseudo-run
  yes:
    validate script
    parse frontmatter
    render prompt
    call claude -p
    call codex exec
    require structured output
    write run logs
    return mapped exit codes

  no, not yet:
    daemon mode
    background scheduling
    remote execution
    implicit dangerous permissions
    automatic installation into every repo
```

Minimum viable command set:

```Bash
apseudo-run --check ./script.apseudo
apseudo-run --render-prompt ./script.apseudo -- target=src
apseudo-run --claude ./script.apseudo -- target=src
apseudo-run --codex ./script.apseudo -- target=src
apseudo-run --dry-run ./script.apseudo -- target=src
```

The `--render-prompt` command is important. It lets you inspect exactly what would be fed to Claude or Codex before allowing the agent to act.

## Bottom line

Yes, this is very feasible.

The correct implementation is not “make pseudocode executable.” It is:

```
make pseudocode files executable as agent task launchers
```

The shebang points to `apseudo-run`; `apseudo-run` validates the script, compiles it into a strict task prompt, launches either `claude -p` or `codex exec`, then parses the structured outcome and exits like a normal CLI tool.

* * *

**You:**

Build this. Include a specification document for reference later.  Also create user instructions for me on all the commands on how to use it.  Also create a document called future versions that outlines what the next versions could include to add features and improve the runners capabilities. GitHub please see my project standards, repository, and GitHub.  Specifically find the CLI documentation standards.  Please use that for the user documentation

* * *

**ChatGPT:**

I’ll add the executable `.apseudo` runner layer, look up your GitHub CLI documentation standard, and package a new release with matching reference and user docs.

I found the active CLI documentation standard and am using its man-style usage structure, synopsis notation, exit-status table, task-first examples, and option-entry format.

Built it as **version 0.5.0** with executable `.apseudo` runner support.

Downloads:

I used your `L3DigitalNet/project-standards` **CLI Documentation Standard** for the user-facing CLI docs: man-style sections, GitHub-style synopsis notation, complete option entries, exit-status tables, environment/files sections, and task-first examples.

## What I added

| Area | Added |
| --- | --- |
| Executable runner | `src/apseudo_lint/runner.py` |
| Shebang/frontmatter parser | `src/apseudo_lint/executable.py` |
| Prompt renderer | `src/apseudo_lint/prompt_renderer.py` |
| Claude adapter | `src/apseudo_lint/agent_adapters/claude.py` |
| Codex adapter | `src/apseudo_lint/agent_adapters/codex.py` |
| Structured outcome schema | `src/apseudo_lint/outcome.py` |
| Console scripts | `apseudo-run`, `apseudo-claude`, `apseudo-codex` |
| Source-tree wrappers | `scripts/apseudo-run`, `scripts/apseudo-claude`, `scripts/apseudo-codex` |
| Example executable script | `examples/executable/fix-ruff.apseudo` |
| Runner tests | `tests/test_runner.py` |
| Specification | `docs/EXECUTABLE-PSEUDOCODE-SPEC.md` |
| User guide | `docs/RUNNER.md` |
| CLI usage reference | `docs/usage.md` |
| Roadmap | `docs/FUTURE-VERSIONS.md` |
| Agent wording updates | `AGENTS.md`, `CLAUDE.md`, `docs/AGENT-INSTRUCTIONS-WORDING.md` |
| Hook hardening | Blocks casual `apseudo-run --danger`, `danger-full-access`, and `APSEUDO_ALLOW_DANGER=1` bypass attempts |

The Claude adapter targets non-interactive `claude -p` usage with JSON output and JSON schema support, matching Claude Code’s documented headless mode behavior. [![](https://www.google.com/s2/favicons?domain=https://code.claude.com&sz=128)Claude](https://code.claude.com/docs/en/headless)

The Codex adapter targets `codex exec`, passes the rendered prompt through stdin using `-`, writes an outcome schema, and supports Codex sandbox modes such as `read-only`, `workspace-write`, and `danger-full-access`. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers+1](https://developers.openai.com/codex/cli/reference)

## How you use it

Example executable pseudocode script:

```
#!/usr/bin/env apseudo-run
---
name: fix_ruff_failures
description: Fix Ruff failures in a bounded, verified loop.
default_agent: codex
mode: apply
workspace: git_root
requires_clean_git: false
codex:
  sandbox: workspace-write
  json: true
claude:
  bare: false
  allowed_tools:
    - Read
    - Edit
    - Bash
  permission_mode: acceptEdits
---

process fix_ruff_failures(target="."):
    diagnostics = run_command("uv run ruff check {target}")

    if diagnostics.empty:
        return Accepted(reason="ruff already passes")

    for diagnostic in diagnostics:
        fix_diagnostic(diagnostic)
        targeted_result = run_command("uv run ruff check {diagnostic.file}")

        if targeted_result.failed:
            return Blocked(reason="targeted Ruff check still fails", evidence=targeted_result.output)

    final_result = run_command("uv run ruff check {target}")

    if final_result.passed:
        return Accepted(reason="all Ruff failures fixed")

    return Blocked(reason="full Ruff check still fails", evidence=final_result.output)
```

Validate without running an agent:

```Bash
uv run apseudo-run --check --codex examples/executable/fix-ruff.apseudo
```

Render the exact prompt that would be sent to the agent:

```Bash
uv run apseudo-run --render-prompt --codex examples/executable/fix-ruff.apseudo -- target=src
```

Show the provider command without running it:

```Bash
uv run apseudo-run --print-command --codex examples/executable/fix-ruff.apseudo -- target=src
```

Run through Codex CLI:

```Bash
uv run apseudo-run --codex --apply examples/executable/fix-ruff.apseudo -- target=src
```

Run through Claude Code:

```Bash
uv run apseudo-run --claude --apply examples/executable/fix-ruff.apseudo -- target=src
```

Run as a shebang script:

```Bash
chmod +x examples/executable/fix-ruff.apseudo
./examples/executable/fix-ruff.apseudo --codex -- target=src
./examples/executable/fix-ruff.apseudo --claude -- target=src
```

Provider-specific aliases are also included:

```Bash
uv run apseudo-codex --apply examples/executable/fix-ruff.apseudo -- target=src
uv run apseudo-claude --apply examples/executable/fix-ruff.apseudo -- target=src
```

## Validation performed

I ran the full project validation suite after adding the runner:

```Bash
uv sync --extra dev
uv run pytest
uv run apseudo-format --check .
uv run apseudo-lint .
uv run apseudo-review .
uv run ruff check src tests .agent-hooks
uv run pyright
scripts/run-enforcement-smoke-test.sh
cd vscode && npm run check && npm run package
unzip -t /mnt/data/agent-pseudocode-syntax-runner-0.5.0.zip
```

Results:

```
45 passed
apseudo-format: checked 53 file(s); no changes.
apseudo-lint: checked 53 file(s); no diagnostics.
apseudo-review: all completeness checks OK.
ruff: All checks passed.
pyright: 0 errors, 0 warnings, 0 informations.
VS Code extension packaged as agent-pseudocode-0.5.0.vsix.
ZIP integrity check passed.
```

I also added fake-provider tests for both Claude and Codex so the runner exercises both provider paths without needing real credentials inside the sandbox.

## Caveat

I validated command construction, prompt rendering, schema writing, fake Claude execution, fake Codex execution, linting, formatting, tests, hooks, and packaging. I could not launch real Claude Code or real Codex CLI from this sandbox, so the remaining local check is to run one real `--render-prompt`, one real `--print-command`, and then one low-risk `--plan` or `--review` execution on your machine.

* * *

**You:**

Are there any other additional features or flags that would be useful to have on the runner? Or other general features to make the overall system more effective request and cohesive.

* * *

**ChatGPT:**

I’ll compare the current runner shape against Claude/Codex invocation surfaces and the rest of the toolchain, then separate “worth adding now” from “interesting but not worth the complexity yet.”

Yes. The runner is viable now, but I would add a **0.6.0 “operational reliability” layer** before adding more language features.

The biggest missing piece is not another agent capability. It is **run traceability**: predictable logs, session IDs, prompt hashes, final output files, changed-file summaries, and resume/replay support.

## Highest-value runner additions

### 1. `--run-dir <path>` and persistent run records

Add a real run directory instead of the current reserved `--log-dir`.

```Bash
apseudo-run --codex --apply ./fix-ruff.apseudo --run-dir .apseudo/runs
```

Each run should create something like:

```
.apseudo/runs/2026-07-08T235940Z-fix-ruff-codex/
├── manifest.json
├── script.apseudo
├── rendered-prompt.md
├── agent-command.json
├── stdout.log
├── stderr.log
├── events.jsonl
├── outcome.json
├── changed-files.txt
├── git-diff.patch
└── validation-after.json
```

This gives you auditability and makes agent runs comparable. It also makes failures easier to debug because you can inspect the exact prompt and command that were used.

### 2. `--output <file>` and `--output-last-message <file>`

Codex already has `--output-last-message`, which writes the assistant’s final message to a file for downstream scripting. The runner should expose a provider-neutral flag and map it to Codex directly. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers](https://developers.openai.com/codex/cli/reference)

```Bash
apseudo-run --codex ./review-spec.apseudo \
  --output .apseudo/outcomes/review-spec.json \
  --output-last-message .apseudo/outcomes/review-spec.md
```

For Claude, the runner can capture JSON output and write equivalent files itself. Claude supports structured JSON output through `--output-format json`, and schema-constrained structured output through `--json-schema`. [![](https://www.google.com/s2/favicons?domain=https://code.claude.com&sz=128)Claude](https://code.claude.com/docs/en/headless)

### 3. `--stream` / `--events <file>`

Add event streaming support.

```Bash
apseudo-run --claude --stream --events .apseudo/runs/latest/events.jsonl ./script.apseudo
apseudo-run --codex --stream --events .apseudo/runs/latest/events.jsonl ./script.apseudo
```

Claude supports `--output-format stream-json` with verbose partial messages for token/event streaming. [![](https://www.google.com/s2/favicons?domain=https://code.claude.com&sz=128)Claude](https://code.claude.com/docs/en/headless) Codex `exec` supports newline-delimited JSON events via `--json`. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers](https://developers.openai.com/codex/cli/reference)

This would make the runner much better for unattended or long-running work.

### 4. `--resume <session-id>` and `--resume-last`

Add session continuation.

```Bash
apseudo-run --claude --resume "$SESSION_ID" ./continue-review.apseudo
apseudo-run --codex --resume-last ./continue-fix.apseudo
```

Claude documents capturing a session ID from JSON output and continuing with `--resume`. [![](https://www.google.com/s2/favicons?domain=https://code.claude.com&sz=128)Claude](https://code.claude.com/docs/en/headless) Codex documents `codex exec resume [SESSION_ID]`, plus `--last` to continue the most recent session from the current working directory. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers](https://developers.openai.com/codex/cli/reference)

For your workflow, this matters because agent tasks often fail halfway through for fixable reasons. A resume-aware runner avoids losing context.

### 5. `--approval-policy <policy>`

Add a provider-neutral approval flag.

```Bash
apseudo-run --codex --approval-policy never ./fix.apseudo
apseudo-run --codex --approval-policy on-request ./fix.apseudo
apseudo-run --claude --approval-policy auto-approved-tools ./fix.apseudo
```

Codex has `--ask-for-approval` with values including `untrusted`, `on-request`, and `never`, and the docs say `never` is preferred for non-interactive runs. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers](https://developers.openai.com/codex/cli/reference) Claude’s equivalent is more permission/tool based: `--allowedTools` can pre-approve specific tools, while other requests abort if not approved. [![](https://www.google.com/s2/favicons?domain=https://code.claude.com&sz=128)Claude](https://code.claude.com/docs/en/headless)

The runner should not pretend the semantics are identical, but it can normalize the intent.

### 6. `--add-dir <path>`

Add this for Codex and represent it in Claude’s prompt contract.

```Bash
apseudo-run --codex --add-dir ../project-standards ./sync-template.apseudo
```

Codex supports `--add-dir` to grant additional directories write access, and the Codex docs recommend preferring `--add-dir` over `danger-full-access` when extra write directories are needed. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers](https://developers.openai.com/codex/cli/reference)

This is particularly relevant to your standards/template-repo drift problem, where a runner may need to read one repo and update another.

### 7. `--ephemeral`

Add a privacy/reproducibility mode for Codex.

```Bash
apseudo-run --codex --ephemeral ./quick-review.apseudo
```

Codex `exec` documents `--ephemeral` for running without persisting session rollout files to disk. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers](https://developers.openai.com/codex/cli/reference)

This is useful for one-off checks, CI, or sensitive repository content.

### 8. `--ignore-user-config` / `--hermetic`

Add a stronger reproducibility mode.

```Bash
apseudo-run --codex --hermetic ./ci-review.apseudo
apseudo-run --claude --hermetic ./ci-review.apseudo
```

For Codex, this should map to `--ignore-user-config` plus explicit runner-supplied config where needed. Codex documents `--ignore-user-config` for avoiding `$CODEX_HOME/config.toml` while still using `CODEX_HOME` for auth. [![](https://www.google.com/s2/favicons?domain=https://developers.openai.com&sz=128)OpenAI Developers](https://developers.openai.com/codex/cli/reference)

For Claude, this should map to `--bare` plus explicit settings, MCP config, allowed tools, and prompt context. Claude’s bare mode skips auto-discovery of hooks, skills, plugins, MCP servers, memory, and `CLAUDE.md`, which makes it useful for scripts where the same result is needed on every machine. [![](https://www.google.com/s2/favicons?domain=https://code.claude.com&sz=128)Claude](https://code.claude.com/docs/en/headless)

I would expose both:

```Bash
--project-context   # use repo instructions/hooks/MCP/skills where supported
--hermetic          # use only runner-specified context
```

### 9. `--require-no-diff` and `--expect-diff`

Add post-run diff policy.

```Bash
apseudo-run --codex --review --require-no-diff ./review-spec.apseudo
apseudo-run --codex --apply --expect-diff ./fix-ruff.apseudo
```

This would catch mismatches between declared mode and actual behavior.

Rules:

```
plan/review mode + diff exists      => fail
apply mode + --expect-diff + no diff => fail or warn
apply mode + validation fails       => fail
```

This is one of the best ways to make the runner cohesive with hooks and CI.

### 10. `--post-check <command>`

Add explicit verification commands after agent completion.

```Bash
apseudo-run --codex --apply ./fix.apseudo \
  --post-check "uv run apseudo-lint ." \
  --post-check "uv run pytest"
```

Even if the pseudocode says to run checks, the runner should be able to enforce checks outside the model loop.

This is different from telling the agent “run tests.” It means the runner itself runs tests after the agent exits.

## Medium-value flags

These are useful, but I would add them after the run-record layer.

| Flag | Purpose |
| --- | --- |
| `--set key=value` | Cleaner alias for script arguments; avoids relying only on positional `-- key=value`. |
| `--arg-file <path>` | Pass structured args from YAML/JSON. |
| `--vars <path>` | Same as arg-file, but explicitly for prompt variables. |
| `--prompt-out <file>` | Write rendered prompt without executing. More scriptable than printing to stdout. |
| `--schema-out <file>` | Write generated outcome schema to a path. |
| `--changed-files-out <file>` | Machine-readable changed files list. |
| `--diff-out <file>` | Write post-run diff patch. |
| `--outcome-format {json,markdown,text}` | Human or machine output selection. |
| `--quiet` | Suppress progress, only show final outcome. |
| `--verbose` | Print command, prompt hash, config source, selected provider, workspace. |
| `--fail-on-warning` | Treat linter warnings as runner failures. |
| `--no-hooks` | Explicitly disable project hooks where possible, but require a visible warning. |
| `--require-hooks` | Fail if provider/project hooks are unavailable or untrusted. |
| `--require-mcp` | Fail if configured MCP tools are not visible to the agent. |
| `--timeout-idle-seconds` | Kill stuck runs with no output/activity. |
| `--max-output-bytes` | Prevent runaway logs. |
| `--lock <name>` | Prevent concurrent runs in the same workspace. |
| `--retry <n>` | Retry provider/transient failures only, not validation failures. |

The two I would prioritize from this set are `--post-check` and `--require-hooks`.

## General system features worth adding

### 1. A script registry: `.apseudo/scripts.toml`

Instead of remembering paths:

```Bash
apseudo-run --codex standards/processes/fix-ruff.apseudo
```

Use named tasks:

```Bash
apseudo run fix-ruff --codex -- target=src
apseudo run review-spec --claude -- spec=docs/spec.md
```

Registry:

```TOML
[scripts.fix-ruff]
path = "standards/processes/fix-ruff.apseudo"
default_agent = "codex"
default_mode = "apply"

[scripts.review-spec]
path = "standards/processes/review-spec.apseudo"
default_agent = "claude"
default_mode = "review"
```

This would make the system feel like `make`, `just`, or `uv run`, but backed by validated agent pseudocode.

### 2. A unified top-level CLI

Right now you have many commands:

```
apseudo-lint
apseudo-format
apseudo-review
apseudo-run
apseudo-mcp
apseudo-lsp
...
```

That is okay for scripting, but the human interface would be cleaner with:

```Bash
apseudo lint .
apseudo format .
apseudo review .
apseudo run fix-ruff --codex
apseudo explain APSEUDO-WHILE-001
apseudo template review-loop
apseudo mermaid standards/processes/review-loop.apseudo
```

Keep the standalone commands for automation, but make `apseudo` the primary user-facing command.

### 3. Real run replay

Add:

```Bash
apseudo-run --replay .apseudo/runs/<run-id>
apseudo-run --rerun .apseudo/runs/<run-id>
apseudo-run --resume-run .apseudo/runs/<run-id>
```

Definitions:

```
--replay      show what happened; no agent execution
--rerun       use same script, args, provider, mode, workspace
--resume-run  continue using stored session id where available
```

This would be very valuable when a headless agent fails after 20 minutes.

### 4. Provider capability probe

Add:

```Bash
apseudo doctor
apseudo doctor --claude
apseudo doctor --codex
```

It should check:

```
- command available
- version
- authentication likely configured
- can run a harmless prompt
- supports required flags
- project hooks trusted/visible
- MCP config visible
- output schema support works
- sandbox mode available
```

This would save a lot of mystery failures.

### 5. Provider parity tests

Create fixture scripts that exercise the same pseudocode through both fake providers and optionally real providers.

```Bash
apseudo provider-test --fake
apseudo provider-test --real --codex
apseudo provider-test --real --claude
```

The runner should report:

```
Claude: pass structured-output smoke
Codex: pass structured-output smoke
Hooks: visible
MCP: visible
```

### 6. Script argument schema

Frontmatter should allow arguments to be declared:

```YAML
args:
  target:
    type: path
    required: false
    default: "."
    description: Path to lint.
  strict:
    type: bool
    default: false
```

Then:

```Bash
apseudo-run ./fix-ruff.apseudo -- target=src strict=true
```

can be validated before the agent sees anything.

This also enables generated help:

```Bash
./fix-ruff.apseudo --help
```

to show script-specific arguments, not just runner options.

### 7. Script-specific `--help`

Executable pseudocode scripts should behave like CLIs:

```Bash
./fix-ruff.apseudo --help
```

Expected output:

```
fix_ruff_failures — Fix Ruff failures in a bounded, verified loop.

Usage:
  fix-ruff.apseudo [RUNNER OPTIONS] -- [target=<path>] [strict=<bool>]

Arguments:
  target  Path to lint. Default: "."
  strict  Treat warnings as failures. Default: false.
```

This would make executable `.apseudo` files much more discoverable.

### 8. Generated README / usage docs from scripts

Add:

```Bash
apseudo docs generate --registry .apseudo/scripts.toml --output docs/agent-tasks.md
```

This would inventory all executable pseudocode tasks in a repo and generate a usage page.

Given your standards focus, this is a natural fit.

### 9. Policy profiles

Add named execution profiles:

```TOML
[profiles.safe-review]
mode = "review"
require_no_diff = true
require_clean_git = false
sandbox = "read-only"

[profiles.local-fix]
mode = "apply"
sandbox = "workspace-write"
post_checks = ["uv run pytest", "uv run ruff check ."]

[profiles.cross-repo-sync]
mode = "apply"
sandbox = "workspace-write"
add_dirs = ["../project-standards", "../template-repo"]
require_clean_git = true
```

Then:

```Bash
apseudo-run --profile local-fix ./fix-ruff.apseudo
```

This is better than repeating long flag sets.

### 10. Better hook integration: runner-aware hooks

The hooks should detect when they are being called from `apseudo-run` and use the run manifest.

Example behavior:

```
- If APSEUDO_RUN_ID is set:
  - write validation results into that run directory
  - include run ID in hook output
  - block bypass attempts with run-aware message
```

This connects the currently separate pieces: runner, hooks, linter, and logs.

## Features I would not add yet

| Feature | Why not yet |
| --- | --- |
| Background daemon | Adds state and failure modes before the runner is mature. |
| Remote execution | Better handled later through SSH/GitHub Actions after local semantics stabilize. |
| Parallel multi-agent execution | Tempting, but hard to reason about with repo mutations. |
| Automatic rollback | Useful, but git stash/worktree policy needs careful design. |
| `danger` defaults in frontmatter | Too risky. Keep danger opt-in at invocation time. |
| Natural-language script args | Keep args explicit and schema-validated. |
| Agent-to-agent handoff inside runner | Better as a future orchestrator, not runner core. |

## My recommended 0.6.0 scope

I would make 0.6.0 about **reliability and auditability**, not more autonomy.

Add:

```
--run-dir
--output
--output-last-message
--events
--stream
--post-check
--require-no-diff
--expect-diff
--add-dir
--approval-policy
--ephemeral
--hermetic / --project-context
--resume / --resume-last
apseudo doctor
script args schema
script-specific --help
```

That would make the runner substantially more practical without turning it into a fragile orchestration platform.

## My recommended 0.7.0 scope

Make the overall system cohesive:

```
- unified `apseudo` top-level command
- `.apseudo/scripts.toml` task registry
- named policy profiles
- generated docs from registered scripts
- run replay/rerun/resume-run
- runner-aware hook logs
- provider parity smoke tests
```

## Core design rule

Do not let the runner become a second policy engine.

The policy should still live in:

```
language standard
+ linter rules
+ script frontmatter
+ repo instructions
+ hooks/CI
```

The runner should coordinate:

```
validate → render → execute → capture → verify → report
```

That separation keeps the system understandable.

* * *

**You:**

Please add all of these features to the project. Use structlog if it makes sense for logging.  This is going to be the last activity for this session   please make sure all features are thoroughly documented with user facing instructions for usage.

* * *

**ChatGPT:**

I’ll extend the runner into a final operational release with run records, registry, unified CLI, richer flags, doctor checks, generated docs, and runner-aware hooks. I’ll preserve existing tooling, validate the package, and provide final user-facing documentation.

I found the existing 0.5.0 project and am upgrading it in-place to a clean 0.6.0 reliability release. The language stays stable while runner orchestration becomes auditable and task-oriented.

Done. I created the final **0.6.0 operational runner release**.

I also rewrote the user-facing CLI documentation using your CLI Documentation Standard’s structure: man-style `NAME`, `SYNOPSIS`, `DESCRIPTION`, `OPTIONS`, `EXIT STATUS`, `ENVIRONMENT`, `FILES`, task-first examples, and complete option entries. The examples follow the same task-first/copy-paste-safe pattern shown in your worked example.

## Added in 0.6.0

| Area | Added |
| --- | --- |
| Runner records | `--run-dir`, run manifests, rendered prompt, provider command, stdout/stderr logs, events, outcome, final message, changed files, diff, post-validation |
| Output controls | `--output`, `--output-last-message`, `--prompt-out`, `--schema-out`, `--events`, `--changed-files-out`, `--diff-out`, `--outcome-format` |
| Provider controls | `--approval-policy`, `--add-dir`, `--ephemeral`, `--resume`, `--resume-last`, `--ignore-user-config`, `--hermetic`, `--project-context` |
| Verification controls | `--post-check`, `--require-no-diff`, `--expect-diff`, `--fail-on-warning`, `--require-hooks`, `--require-mcp` |
| Reliability controls | `--timeout-seconds`, `--timeout-idle-seconds`, `--max-output-bytes`, `--lock`, `--retry`, `--stream` |
| Script args | frontmatter argument schema, `--set`, `--arg-file`, `--vars`, script-specific `--help` |
| Registry | `.apseudo/scripts.toml`, named tasks, `apseudo run <name>` |
| Unified CLI | `apseudo lint`, `apseudo format`, `apseudo review`, `apseudo run`, `apseudo doctor`, `apseudo provider-test`, `apseudo docs generate` |
| Logging | optional `structlog` support with standard-library fallback |
| Hooks | runner-aware hook audit via `APSEUDO_RUN_ID` and `APSEUDO_RUN_DIR` |
| Docs | updated `docs/usage.md`, `docs/RUNNER-USAGE.md`, `docs/EXECUTABLE-PSEUDOCODE-SPEC.md`, `docs/FUTURE-VERSIONS.md`, `docs/AGENT-INSTRUCTIONS-WORDING.md`, `docs/agent-tasks.md` |

## Key usage examples

Validate a script:

```Bash
uv run apseudo-run --check examples/runner/fix-ruff.apseudo
```

Inspect the exact prompt:

```Bash
uv run apseudo-run --codex --render-prompt examples/runner/fix-ruff.apseudo -- target=src
```

Run a registered task with run records and post-checks:

```Bash
uv run apseudo run fix-ruff \
  --codex \
  --apply \
  --run-dir .apseudo/runs \
  --post-check "uv run ruff check src tests .agent-hooks" \
  --post-check "uv run pytest" \
  --expect-diff \
  -- target=src
```

Review without allowing changes:

```Bash
uv run apseudo-run --claude --review \
  --require-no-diff \
  --run-dir .apseudo/runs \
  examples/runner/review-spec.apseudo -- spec=docs/spec.md
```

Generate docs from the task registry:

```Bash
uv run apseudo docs generate --output docs/agent-tasks.md
```

Use the shebang behavior:

```Bash
chmod +x examples/runner/fix-ruff.apseudo
./examples/runner/fix-ruff.apseudo --help
./examples/runner/fix-ruff.apseudo --codex --apply -- target=src
```

## Validation performed

I ran:

```Bash
uv sync --extra dev
uv run pytest -q
uv run apseudo-format --check .
uv run apseudo-lint .
uv run apseudo-review .
uv run ruff check src tests .agent-hooks
uv run pyright
scripts/run-enforcement-smoke-test.sh
cd vscode && npm run check && npm run package
unzip -t /mnt/data/agent-pseudocode-syntax-runner-0.6.0.zip
```

Results:

```
50 passed
apseudo-format: checked 54 file(s); no changes.
apseudo-lint: checked 54 file(s); no diagnostics.
apseudo-review: 0 diagnostics; completeness checks OK.
ruff: All checks passed.
pyright: 0 errors, 0 warnings, 0 informations.
VS Code extension packaged as agent-pseudocode-0.6.0.vsix.
ZIP integrity check passed.
```

I also ran the fake-provider adapter path:

```Bash
uv run apseudo provider-test --json
```

Both Claude and Codex adapter paths returned `Accepted` through fake providers.

One caveat: I validated command construction, prompt rendering, fake Claude/Codex execution, schema handling, run records, docs, tests, hooks, packaging, and static checks in the sandbox. I could not run real Claude Code or real Codex CLI here, so the remaining local check is one low-risk real run, ideally `--review --require-no-diff --run-dir .apseudo/runs`, after trusting/enabling project hooks locally.

* * *

**You:**

Failed to get upload status for /mnt/data/agent-pseudocode-syntax-runner-0.6.0

* * *

**ChatGPT:**

That error is likely because `/mnt/data/agent-pseudocode-syntax-runner-0.6.0` is a **folder**, not the uploaded downloadable file.

Use the zip link instead:

VS Code extension package:

I verified both files exist in `/mnt/data`.

* * *

**You:**

I will eventually be converting this to a proper project-standards packaged standard; however, until I have it tested and further developed a bit I will developing and maintaining it in it's own GitHub repo. Can you please restructure the directory structure to:
- minimize loose files in the repo root
- put the distribution/product files and directories into a common folder to minimize root sprawl. 
- clean up the docs/ folder by logically grouping into folders, examples:
  - docs/specs
  - docs/usage
- generally try to keep related files together as much as possible (without breaking it).

* * *

**ChatGPT:**

I’ll restructure the generated repo as a GitHub-project-friendly layout, keep root files to the minimum needed for tooling discovery, update paths/configs/docs, then run the validation suite and package a new zip.

The root is now reduced to conventional discovery/config files plus `src`, `tests`, `scripts`, `docs`, `products`, and `integrations`. I moved editor products under `products/`, examples/specs under `docs/`, and the shared hook implementation under `integrations/agent-hooks/`.

Done. I restructured it as a cleaner standalone GitHub repo layout and packaged it as **0.6.1**.

Downloads:

## Main structure changes

| Area | New location |
| --- | --- |
| VS Code extension | `products/vscode-extension/` |
| Kate integration | `products/kate-integration/` |
| Shared Claude/Codex hook implementation | `integrations/agent-hooks/` |
| Language convention/spec docs | `docs/specs/` |
| User-facing docs | `docs/usage/` |
| Feature docs | `docs/features/` |
| Enforcement docs | `docs/enforcement/` |
| Examples | `docs/examples/` |
| Review/audit docs | `docs/reviews/` |
| Future-version docs | `docs/roadmap/` |
| Source register | `docs/reference/` |

I also added:

* `docs/README.md` — documentation index.
* `docs/usage/REPOSITORY-LAYOUT.md` — explains why each remaining root item stays at root.
* `products/README.md` — explains product/editor integration grouping.

The root now keeps only conventional/discovery files and major project directories:

```
AGENTS.md
CLAUDE.md
CHANGELOG.md
LICENSE
README.md
pyproject.toml
uv.lock
.apseudo/
.claude/
.codex/
.agents/
.github/
docs/
integrations/
products/
scripts/
src/
tests/
```

## Validation performed

I ran the full validation path after restructuring:

```Bash
uv sync --extra dev
uv run pytest
uv run apseudo-format --check .
uv run apseudo-lint .
uv run apseudo-review .
uv run ruff check src tests integrations/agent-hooks
uv run pyright
scripts/run-enforcement-smoke-test.sh
cd products/vscode-extension && npm run package
unzip -t /mnt/data/agent-pseudocode-syntax-runner-0.6.1-layout.zip
```

Results:

```
47 passed
apseudo-format: checked 57 file(s); no changes.
apseudo-lint: checked 57 file(s); no diagnostics.
apseudo-review: all completeness checks OK.
ruff: All checks passed.
pyright: 0 errors, 0 warnings, 0 informations.
VS Code extension packaged as agent-pseudocode-0.6.1.vsix.
ZIP integrity check passed.
```

I did not run real Claude Code, Codex CLI, VS Code UI, or Kate UI in this sandbox; the static/tooling validation and packaging passed.

* * *

**You:**

Earlier in this chat I gave you the following prompt/response: "Help me understand how it’s best to use this. Please give me usage examples of when I would use one of the pseudo or agent pseudo scripts. How does it get involved? How is it fed to the agent?"

The response you provided was very good and useful. Can you please create a set of comprehensive documents like this that give use cases, examples, etc.? Please make them relevant to everything shipped in 0.6.1.

* * *

**ChatGPT:**

I’ll add a usage-playbook documentation set under `docs/usage/`, centered on how pseudocode gets used, when to choose each surface, and how 0.6.1 components feed Claude/Codex.

Done. I created a comprehensive usage-playbook documentation set for **0.6.1** and packaged the updated project.

## Added documents

New folder:

```
docs/usage/use-cases/
```

New documents:

| Document | Purpose |
| --- | --- |
| `docs/usage/use-cases/README.md` | Index and recommended reading order. |
| `docs/usage/use-cases/MENTAL-MODEL.md` | Explains what Agent Pseudocode is, what it is not, and how it becomes actionable. |
| `docs/usage/use-cases/CHOOSING-A-SURFACE.md` | Decision guide for prose vs Markdown fenced blocks vs `.apseudo` files vs executable runner scripts vs MCP/hooks/CI. |
| `docs/usage/use-cases/AGENT-FEEDING-PATHS.md` | Explains exactly how pseudocode is fed to Claude Code and Codex CLI through prompts, repo context, runner scripts, hooks, MCP, skills, and editor tooling. |
| `docs/usage/use-cases/COMMON-WORKFLOWS.md` | Concrete workflow examples: spec review, Ruff repair, handoff-size control, upstream bugs, release gates, template sync, docs repair, and policy audit. |
| `docs/usage/use-cases/RUNNER-WORKFLOWS.md` | Practical `apseudo-run` usage patterns, safe first-run sequence, run records, registry tasks, post-checks, diff policy, replay/resume, and troubleshooting. |
| `docs/usage/use-cases/REPOSITORY-OPERATING-MODEL.md` | How to adopt the system in a real repo while it is maintained outside `project-standards`. |
| `docs/usage/use-cases/EXAMPLE-CATALOG.md` | Copy-adaptable patterns for bounded review loops, size reduction, verification, release gates, cross-repo sync, and prompt wording. |
| `docs/usage/README.md` | New user-docs index tying the usage docs together. |

I also updated:

```
docs/README.md
CHANGELOG.md
```

## Validation performed

I ran:

```Bash
uv sync --extra dev
uv run pytest -q
uv run apseudo-format --check .
uv run apseudo-lint .
uv run apseudo-review .
uv run ruff check src tests integrations/agent-hooks
uv run pyright
scripts/run-enforcement-smoke-test.sh
unzip -t /mnt/data/agent-pseudocode-syntax-runner-0.6.1-usage-docs.zip
```

Results:

```
47 passed
apseudo-format: checked 67 file(s); no changes.
apseudo-lint: checked 67 file(s); no diagnostics.
apseudo-review: 0 diagnostics; completeness checks OK.
ruff: All checks passed.
pyright: 0 errors, 0 warnings, 0 informations.
Enforcement smoke test passed.
ZIP integrity check passed.
```

The package excludes local `.venv`, `node_modules`, caches, and other generated working directories.

<!-- prettier-ignore-end -->
