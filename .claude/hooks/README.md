# Claude Code hook notes

This project uses `.claude/settings.json` to wire Claude Code lifecycle events to the shared `integrations/agent-hooks/apseudo-hook.py` runner.

Configured events:

- `SessionStart`: injects a short reminder that pseudocode enforcement is active.
- `PostToolUse`: runs after file edits and validates changed pseudocode files.
- `Stop`: runs before the final response and blocks/continues if pseudocode errors remain.

The hook command uses `${CLAUDE_PROJECT_DIR}` so it keeps working when Claude Code starts from a subdirectory.
