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

## User Managed

- [ ] Adopt [agent-handoff-v3](https://github.com/chrisdpurcell/agent-handoff-v3)
- [ ] Adopt the following standards from [project-standards](https://github.com/L3DigitalNet/project-standards/tree/main/standards) (official releases only, do not adopt from the testing/dev branch):
  - [ ] adr **Note:** use `docs/adr`, not `docs/decisions` as the ADR folder.
  - [ ] markdown-tooling
  - [ ] cli-documentation
  - [ ] project-spec
  - [ ] python-tooling
  - [ ] python-coding
- [ ] Setup GitHub repository settings; see `/home/chris/Downloads/public-repo-settings.md`
- [ ] Ingest/migrate existing specs from `docs/specs` into the project-spec format.
- [ ] Create specification documents from the existing project state. See `docs/reference`.
  - Some reverse-engineering may be required.
  - It is important to capture the current state of the project in a specification document to ensure that future development aligns with the intended design and functionality. It also provides a baseline for future reference and helps maintain consistency in the project's evolution.
  - Create multiple specification documents if necessary to cover different aspects of the project. Size/scope them appropriately to ensure clarity and comprehensiveness.
  - Ensure the specs comply with the project-spec standard.
- [ ] Correct naming of markdown files in `docs/` (except README.md) to use lower kebab-case. Ensure all links and references are updated accordingly.

## Agent Managed

## Completed Tasks
