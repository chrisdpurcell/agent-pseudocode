---
schema_version: '1.1'
id: 'reference-8rgc2s-scope-map-agent-pseudocode'
title: 'Scope Map: Agent Pseudocode'
description: 'Reference map for scopes in Pythonic Agent Pseudocode.'
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
aliases:
  - 'scope map'
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Scope Map: Agent Pseudocode

| Token class | Examples | VS Code TextMate scope | Kate item style |
| --- | --- | --- | --- |
| Comment | `# explain intent` | `comment.line.number-sign.agent-pseudocode` | `dsComment` |
| Docstring | `"""notes"""` | `string.quoted.docstring.multi.agent-pseudocode` | `dsDocumentation` |
| String | `"approved"` | `string.quoted.double.agent-pseudocode` | `dsString` |
| Process declaration keyword | `process`, `def` | `keyword.declaration.function.agent-pseudocode` | `dsKeyword` |
| Process/function name | `review_loop` | `entity.name.function.agent-pseudocode` | `dsFunction` |
| Control keyword | `if`, `while`, `return` | `keyword.control.agent-pseudocode` | `dsControlFlow` |
| Logical operator | `and`, `or`, `not` | `keyword.operator.logical.agent-pseudocode` | `dsOperator` |
| Normative keyword | `MUST`, `SHOULD NOT` | `keyword.other.normative.agent-pseudocode` | `dsAlert` |
| Outcome constructor | `Accepted`, `Blocked` | `support.class.outcome.agent-pseudocode` | `dsDataType` |
| Built-in constant | `True`, `False`, `None` | `constant.language.agent-pseudocode` | `dsConstant` |
| Number | `5`, `3.14` | `constant.numeric.agent-pseudocode` | `dsDecVal` / `dsFloat` |
| Agent action call | `run_tests(...)` | `entity.name.function.call.agent-pseudocode` | `dsFunction` |
| Operator | `==`, `<=`, `+=` | `keyword.operator.agent-pseudocode` | `dsOperator` |
| Annotation | `@requires_review` | `meta.annotation.agent-pseudocode` | `dsAnnotation` |
