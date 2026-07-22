---
bug_id: '004'
date: '2026-07-09'
title: 'lsp.py serve() loop leaves _read_message unwrapped by try/except'
services: [lsp]
status: open
---

## Cause

`src/apseudo_lint/lsp.py`'s `serve()` (line 83) calls `self._read_message()` (line 87, defined at line 98) outside any `try`/`except` — only `_handle_message(message)` (line 91, defined at line 116) is guarded. A malformed incoming message (truncated Content-Length body, invalid JSON) raises inside `_read_message` uncaught, and the process terminates via Python's default unhandled-exception path (traceback to stderr, exit code 1) instead of degrading gracefully like the rest of the server's documented exit-code contract (0/1/2, per `docs/apseudo-docs/usage/usage.md`'s `apseudo-lsp` entry, added 2026-07-09).

Found via source-verification during a cli-documentation-standard adoption task (2026-07-09): confirmed by reading `_read_message`'s implementation, not by reproducing a crash at runtime.

## Fix

Not yet applied. Likely fix: wrap the `_read_message()` call (or its body) in the same `try`/`except` pattern already used for `_handle_message`, and decide the correct behavior on a malformed message — most language-server protocols expect the server to log and continue (skip the bad message) or exit cleanly with a distinguishable code, not traceback.

## Lesson

When documenting a CLI/server's exit-status contract from source (rather than from existing docs), read the whole message-loop, not just the handler function — an unguarded call one level up from the "main" handler is an easy path to miss, and it's exactly the kind of gap a documentation task can surface without being the task that fixes it.
