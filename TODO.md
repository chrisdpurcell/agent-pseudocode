# TODO.md

<!--
Purpose:
- This document is used to track tasks that need to be completed. It is intended to be a user-facing document that provides transparency about what the agent is working on and what tasks are still pending.

Instructions for AI agents:
- Do not add tasks to the `## User Managed` section.
- Do add tasks to the `## Agent Managed` section. Must include all open tasks from the agent-managed handoff document(s).
- Use `- [ ]` to indicate an open task and mark `- [x]` upon completion.
- For partially completed tasks, append a brief log of what has been done and what remains to be done to close the task. The agent should provide update comments for both `## User Managed` and `## Agent Managed` sections.
- Move completed tasks to the `## Completed Tasks` section at the end of the session, but not before. This allows the user to see what has been completed during the session.
-->

## User Tracked Tasks

- [x] Adopt [agent-handoff-v3](https://github.com/chrisdpurcell/agent-handoff-v3)
- [x] Adopt the following standards from [project-standards](https://github.com/L3DigitalNet/project-standards/tree/main/standards) (official releases only, do not adopt from the testing/dev branch):
  - [x] adr **Note:** use `docs/adr`, not `docs/decisions` as the ADR folder.
  - [x] markdown-tooling
  - [x] cli-documentation
  - [x] project-spec
  - [x] python-tooling
  - [x] python-coding
- [x] Relocated the existing `docs/specs/*.md` language-reference material
  (`PYTHONIC_PSEUDOCODE_STANDARD.md`, `EXECUTABLE-PSEUDOCODE-SPEC.md`,
  `RULES.md`, `docs/specs/language/`) to `docs/reference/` rather than
  migrating it into project-spec format — per ADR-0001, this content is
  durable, normative reference documentation, not a project plan.
  `project-spec` was adopted for new, forward-looking specs authored under
  `docs/specs/` going forward.
- [ ]

## Agent Tracked Tasks

- [ ] Task 9: Full-repo Markdown cleanup — run `npx prettier@3.8.3 --write .`
  and `npx markdownlint-cli2 --fix "**/*.md"` across all 83 tracked Markdown
  files (489 pre-existing violations found across 33 files as of the
  markdown-tooling adoption), review the diff, then re-add
  `.github/workflows/lint-markdown.yml` (deleted after the adopt CLI wrote
  it) and flip `.github/workflows/format.yml`'s `prettier` input from
  `false` to `true`.

- [ ] Task 10: Raise test coverage to the `python-tooling` standard's
  `fail_under = 85` floor. Actual coverage as of the python-tooling adoption
  is **60%** (`src/apseudo_lint` total, `coverage report` output), with the
  weakest modules at or near 0%: `__main__.py` (0%), `explain_cli.py` (0%),
  `output.py` (0%), `template_cli.py` (0%), `discover.py` (16%),
  `cli.py` (16%), `format_cli.py` (13%), `mermaid.py` (20%),
  `mermaid_cli.py` (29%), `lsp.py` (42%), `mcp.py` (39%). `apseudo-lint.yml`'s
  new `Run coverage` step (added by the python-tooling adoption) will fail
  CI on every push/PR until this gap is closed — writing the missing tests
  is a substantial, separate body of work, out of scope for a tooling-config
  adoption task.

- [ ] Author the first project-spec-conformant spec under `docs/specs/` and
  add `.github/workflows/validate-specs.yml` (deferred from project-spec
  adoption, 2026-07-08 — the standard refuses an empty corpus rather than
  passing vacuously, so wiring CI before any spec exists would fail every
  run).

## Completed Tasks
