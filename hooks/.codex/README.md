# Codex hook notes

Codex discovers project hooks from `.codex/hooks.json` after the project `.codex/` layer is trusted.

Configured events:

- `SessionStart`: injects pseudocode enforcement context.
- `PostToolUse`: runs after Bash/apply_patch/Edit/Write activity and validates changed pseudocode files.
- `Stop`: runs before the turn ends and asks Codex to continue if pseudocode errors remain.

In Codex, open `/hooks` to inspect and trust changed hook definitions.
