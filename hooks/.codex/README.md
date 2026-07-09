# Dormant Codex hook notes

This directory keeps the project agent-pseudocode Codex hook definitions out of
active discovery. Codex discovers active project hooks from `.codex/hooks.json`
after the project `.codex/` layer is trusted.

The dormant hook definitions in `hooks.json` cover these events:

- `SessionStart`: injects pseudocode enforcement context.
- `PostToolUse`: runs after Bash/apply_patch/Edit/Write activity and validates changed pseudocode files.
- `Stop`: runs before the turn ends and asks Codex to continue if pseudocode errors remain.

If these hooks are restored to `.codex/hooks.json`, open `/hooks` in Codex to
inspect and trust changed hook definitions.
