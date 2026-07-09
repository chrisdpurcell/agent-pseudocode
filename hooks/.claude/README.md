---
schema_version: '1.1'
id: 'index-bujd3h-dormant-claude-code-hook-notes'
title: 'Dormant Claude Code hook notes'
description: 'Notes for dormant Claude Code hook definitions parked outside active discovery.'
doc_type: 'index'
status: 'active'
created: '2026-07-09'
updated: '2026-07-09'
reviewed: null
owner: 'tooling-maintainers'
consumer: 'agent'
tags:
  - 'agent-hooks'
  - 'hooks'
  - 'enforcement'
aliases:
  - 'Claude Code hooks'
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Dormant Claude Code hook notes

This directory keeps the project agent-pseudocode Claude Code hook definitions out of active discovery. Claude Code reads `.claude/settings.json`; the root settings file is reserved for the active agent-handoff-v3 SessionStart hook.

The dormant hook definitions in `settings.json` wire these events to the shared `integrations/agent-hooks/apseudo-hook.py` runner:

- `SessionStart`: injects a short reminder that pseudocode enforcement is active.
- `PostToolUse`: runs after file edits and validates changed pseudocode files.
- `Stop`: runs before the final response and blocks/continues if pseudocode errors remain.

The hook commands use `${CLAUDE_PROJECT_DIR}` so they keep working when Claude Code starts from a subdirectory.
