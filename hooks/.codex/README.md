---
schema_version: '1.1'
id: 'index-gb0llg-dormant-codex-hook-notes'
title: 'Dormant Codex hook notes'
description: 'Notes for dormant Codex hook definitions parked outside active discovery.'
doc_type: 'index'
status: 'active'
created: '2026-07-09'
updated: '2026-07-09'
reviewed: null
owner: 'tooling-maintainers'
consumer: 'agent'
tags:
  - 'agent-hooks'
  - 'codex'
  - 'hooks'
  - 'enforcement'
aliases:
  - 'Codex hooks'
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Dormant Codex hook notes

This directory keeps the project agent-pseudocode Codex hook definitions out of active discovery. Codex discovers active project hooks from `.codex/hooks.json` after the project `.codex/` layer is trusted.

The dormant hook definitions in `hooks.json` cover these events:

- `SessionStart`: injects pseudocode enforcement context.
- `PostToolUse`: runs after Bash/apply_patch/Edit/Write activity and validates changed pseudocode files.
- `Stop`: runs before the turn ends and asks Codex to continue if pseudocode errors remain.

If these hooks are restored to `.codex/hooks.json`, open `/hooks` in Codex to inspect and trust changed hook definitions.
