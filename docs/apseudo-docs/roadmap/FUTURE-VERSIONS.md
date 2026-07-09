---
schema_version: '1.1'
id: 'note-9axn0p-future-versions'
title: 'Future Versions'
description: 'Roadmap note for future Pythonic Agent Pseudocode versioning.'
doc_type: 'note'
status: 'active'
created: '2026-07-08'
updated: '2026-07-09'
reviewed: null
owner: 'agent-pseudocode-maintainers'
consumer: 'mix'
tags:
  - 'documentation'
aliases: []
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Future Versions

Date: 2026-07-09  
Applies to: Agent Pseudocode Toolkit `0.6.1`

## Current baseline

Version `0.6.1` adds the operational runner layer: persistent run records, output/event files, stream capture, provider resume flags, post-checks, diff policy, script argument schema, script-specific help, registry tasks, unified `apseudo`, provider doctor, provider-test, docs generation, and run-aware hook audit.

The next versions should focus on correctness, portability, and provider parity rather than more autonomy.

## 0.7.0 — Runner hardening

Recommended scope:

- Replace best-effort provider flag mappings with version-detected provider capability profiles.
- Add `apseudo doctor --real` smoke tests that run harmless live Claude/Codex prompts.
- Capture provider session IDs into `manifest.json` for reliable `--resume-run`.
- Add idle-timeout enforcement for streaming mode.
- Add before/after Git snapshot comparison so diff policy can distinguish pre-existing changes from agent-created changes.
- Add structured run-summary Markdown generation from run records.
- Add `--dry-run` as an alias for `--render-prompt --print-command` style preview output.
- Add JSON Schema validation for frontmatter itself.

## 0.8.0 — Registry and profile maturity

Recommended scope:

- Support named policy profiles in `.apseudo/scripts.toml`, such as `safe-review`, `local-fix`, and `cross-repo-sync`.
- Add `apseudo run <name> --profile <policy>` where policy expands sandbox, hooks, MCP, post-check, diff, and logging defaults.
- Add registry validation: missing paths, duplicate names, unsupported default agents, invalid modes.
- Generate richer task documentation including script argument descriptions, modes, provider defaults, and examples.
- Add shell completions for registered task names.

## 0.9.0 — Parser and semantic enforcement

Recommended scope:

- Replace regex-like structural checks with a real parser for the Pythonic pseudocode subset.
- Build a control-flow graph for each `process`.
- Prove every terminal path reaches an approved outcome.
- Prove bounded loops update loop-control state.
- Validate `run_command(...)` and mutating actions against declared verification requirements.
- Add linter autofix suggestions exposed through the language server.

## 1.0.0 — Stable internal standard

Release `1.0.0` when:

- Claude and Codex real-provider smoke tests pass on supported platforms.
- VS Code extension, Kate syntax, linter, formatter, LSP, MCP, hooks, runner, registry, and docs all trace to the same rule catalog.
- The CLI usage reference is generated or drift-checked against parser definitions.
- The project has a stable compatibility policy for script frontmatter and linter rule IDs.
- The runner has safe defaults and does not require hidden operator knowledge.

## Not recommended yet

Defer these until after `1.0.0`:

- background daemon mode;
- remote execution;
- automatic rollback beyond Git diff capture;
- parallel multi-agent mutation of one workspace;
- agent-to-agent orchestration inside `apseudo-run`;
- automatic production deploy workflows.

Those features add meaningful operational risk and should be built only after the local runner has stable auditability and provider parity.
