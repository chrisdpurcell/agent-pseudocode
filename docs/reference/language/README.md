---
schema_version: '1.1'
id: 'index-ofpar3-language-spec-directory'
title: 'Language Spec Directory'
description: 'Index for Pythonic Agent Pseudocode language reference documents.'
doc_type: 'index'
status: 'active'
created: '2026-07-09'
updated: '2026-07-09'
reviewed: null
owner: 'docs-maintainers'
consumer: 'mix'
tags:
  - 'index'
  - 'reference'
  - 'language'
aliases: []
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Language Spec Directory

This directory is the shared source of truth for the editor adapters.

- `TOKEN-SPEC.md` defines what the language recognizes.
- `SCOPE-MAP.md` maps tokens to VS Code and Kate style concepts.
- `examples/` contains canonical sample files used to test highlighters.

When adding a new keyword or outcome name, update this directory first, then update the VS Code grammar and Kate XML.
