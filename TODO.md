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

- [ ] Adopt [agent-handoff-v3](https://github.com/chrisdpurcell/agent-handoff-v3)
- [ ] Adopt the following standards from [project-standards](https://github.com/L3DigitalNet/project-standards/tree/main/standards) (official releases only, do not adopt from the testing/dev branch):
  - [ ] adr **Note:** use `docs/adr`, not `docs/decisions` as the ADR folder.
  - [ ] markdown-tooling
  - [ ] cli-documentation
  - [ ] project-spec
  - [ ] python-tooling
  - [ ] python-coding
- [ ] Ingest/migrate existing specs from `docs/reference` into the project-spec format.
- [ ]

## Agent Tracked Tasks

- [ ] Task 9: Full-repo Markdown cleanup — run `npx prettier@3.8.3 --write .`
  and `npx markdownlint-cli2 --fix "**/*.md"` across all 83 tracked Markdown
  files (489 pre-existing violations found across 33 files as of the
  markdown-tooling adoption), review the diff, then re-add
  `.github/workflows/lint-markdown.yml` (deleted after the adopt CLI wrote
  it) and flip `.github/workflows/format.yml`'s `prettier` input from
  `false` to `true`.

## Completed Tasks
