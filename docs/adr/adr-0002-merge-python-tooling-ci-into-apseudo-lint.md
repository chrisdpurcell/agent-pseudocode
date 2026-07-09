---
schema_version: '1.1'
id: 'adr-0002-agent-pseudocode-merge-python-tooling-ci-into-apseudo-lint'
title: 'ADR 0002: Merge python-tooling CI Expectations into apseudo-lint.yml Instead of a Separate check.yml'
description: 'Decision record for updating the existing apseudo-lint.yml workflow in place with python-tooling standard steps rather than adding a second, overlapping CI workflow.'
doc_type: 'adr'
status: 'active'
created: '2026-07-09'
updated: '2026-07-09'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'ci'
  - 'python-tooling'
  - 'adr'
  - 'exception'
aliases: []
related:
  - 'docs/adr/adr-0001-relocate-language-reference-docs.md'
supersedes: []
superseded_by: null
source:
  - '.superpowers/sdd/task-7-brief.md'
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers: []
  consulted: []
  informed: []
---

# ADR 0002: Merge python-tooling CI Expectations into apseudo-lint.yml Instead of a Separate check.yml

## Context and Problem Statement

The `python-tooling` standard (§19.2/§21 of `standards/python-tooling/README.md` in `project-standards`) expects consumers to add a dedicated `.github/workflows/check.yml` running `ruff check`, `ruff format --check`, `basedpyright`, `pytest`, `coverage`, and `pip-audit`. This repository already runs an equivalent Python quality gate — `pytest`, `ruff check`, and a type checker (`pyright`, now `basedpyright`) — as steps inside one consolidated workflow, `.github/workflows/apseudo-lint.yml`, alongside the pseudocode-specific checks (`apseudo-format`, `apseudo-lint`, `apseudo-review`, CLI entry-point smoke tests, JSON/TOML config validation) that are this repo's primary CI purpose. Should this repository add a second, separate `check.yml` workflow as the standard's default prescribes, or extend the existing `apseudo-lint.yml` in place?

## Decision Drivers

- Avoid duplicate/overlapping CI jobs that both check out the repo, set up Python, and run `uv sync` — wasted CI minutes and two sources of truth for "is Python code OK."
- This repo's primary CI concern is validating the Pythonic Agent Pseudocode standard itself; Python-implementation quality gates are a secondary, supporting concern for the tooling that implements that validation, not a separate top-level concern.
- The `python-tooling` standard's own §20 exceptions process explicitly permits a documented deviation when a project already has an equivalent, functioning gate.

## Considered Options

- Add a new `.github/workflows/check.yml` exactly matching the standard's default template, running alongside `apseudo-lint.yml`.
- Update `apseudo-lint.yml` in place: bump Python to 3.14, swap `pyright` for `basedpyright`, and add `coverage` + `pip-audit` steps to the existing job.

## Decision Outcome

Chosen option: "Update `apseudo-lint.yml` in place," because a second workflow would duplicate the checkout/Python-setup/`uv sync` preamble that `apseudo-lint.yml` already performs, and would create two independent "is this repo's Python code correct" signals instead of one. This repo's CI already checks out, sets up Python, and runs `uv sync --extra dev` once; folding the `python-tooling` steps into that same job keeps a single canonical gate and a single place to look when CI is red.

### Consequences

- Good, because CI stays as one job with one Python setup, avoiding duplicated setup time and duplicated failure surfaces.
- Good, because the pseudocode-specific and Python-quality checks run against the exact same `uv sync` state, eliminating drift between two separately-synced environments.
- Bad, because a `python-tooling`-standard-only consumer of this repo (e.g., someone scanning for `check.yml` by convention) will not find the expected filename; this ADR is the documented pointer to where those checks actually live.
- Bad, because if `apseudo-lint.yml`'s job ever needs to be split (e.g., matrix testing multiple Python versions for the Python tooling but not the pseudocode checks), the merge will need to be undone.

### Confirmation

Compliance is confirmed by `apseudo-lint.yml` containing, in one job: `uv run pytest`, `uv run ruff check ...`, `uv run basedpyright`, `uv run coverage run -m pytest && uv run coverage report`, and `uv run pip-audit` — the same checks §19.2 lists for `check.yml`, just co-located with the pseudocode-specific steps instead of split into a second file.

## Pros and Cons of the Options

### Separate `check.yml`

- Good, because it matches the standard's default template byte-for-byte, so no exception needs to be recorded.
- Bad, because it duplicates checkout/Python-setup/`uv sync` (CI minutes, cache misses) that `apseudo-lint.yml` already performs.
- Bad, because it creates two "Python is broken" signals (one per workflow) instead of one, increasing the chance a red check is overlooked in one workflow while the other is green.

### Merge into `apseudo-lint.yml`

- Good, because it reuses the existing checkout/Python-setup/`uv sync` steps, so no CI time or resolution work is duplicated.
- Good, because contributors have exactly one workflow to check for "did my change break anything."
- Neutral, because it requires this ADR to document the deviation per the standard's §20 exceptions process — a one-time cost, not an ongoing one.

## More Information

This deviation is scoped to workflow *file layout* only; the standard's required *checks* (`ruff check`, `basedpyright`, `pytest`, `coverage`, `pip-audit`) are all present, just inside `apseudo-lint.yml` rather than a dedicated `check.yml`. Revisit this decision if the pseudocode-specific and Python-tooling checks ever need independent trigger conditions (e.g., different `paths:` filters) or a matrix build, at which point splitting them back into two workflows would resolve the "Bad" consequences above.
