---
schema_version: '1.1'
id: 'adr-0003-agent-pseudocode-markdown-frontmatter-scope-and-conventions'
title: 'ADR 0003: Govern Durable Markdown Frontmatter Scope and Conventions'
description: 'Decision for the durable Markdown frontmatter corpus and metadata conventions.'
doc_type: 'adr'
status: 'active'
created: '2026-07-09'
updated: '2026-07-09'
reviewed: '2026-07-09'
owner: 'agent-pseudocode-maintainers'
consumer: 'mix'
tags:
  - 'adr'
  - 'documentation'
  - 'frontmatter'
  - 'standards-adoption'
aliases:
  - 'ADR 0003'
  - 'Markdown frontmatter conventions'
  - 'Frontmatter scope'
related:
  - '.project-standards.yml'
  - 'TODO.md'
  - 'docs/handoff/conventions.md'
  - 'docs/adr/adr-0001-relocate-language-reference-docs.md'
supersedes: []
superseded_by: null
source:
  - 'TODO.md'
  - '.project-standards.yml'
  - 'docs/handoff/conventions.md'
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers: []
  consulted: []
  informed: []
---

# Govern Durable Markdown Frontmatter Scope and Conventions

## Context and Problem Statement

This repository adopted the `markdown-frontmatter` standard narrowly as a prerequisite for the `adr` standard. The current `.project-standards.yml` frontmatter scope is limited to `docs/adr/**/*.md`, and `docs/handoff/conventions.md` C-004 explicitly warns not to widen that scope without a separate decision.

The repository now needs a repo-specific convention for how frontmatter should apply beyond ADRs. The problem is not just "which globs should validate." This repo carries several kinds of Markdown with different lifetimes:

- durable documentation that should be searchable, classifiable, and validated;
- executable or harness-owned instruction files that have their own metadata contracts;
- session-state and work-tracking files that are operational, not a durable documentation corpus;
- scratchpads, review artifacts, plans, and fixtures that should remain temporary or behavior-preserving.

Which Markdown files should become governed documents, which files should stay outside the frontmatter corpus, and how should governed documents be classified?

## Decision Drivers

- Keep the durable documentation corpus discoverable for humans and agents without forcing metadata onto operational files.
- Avoid widening validation into temporary work products that should be deleted when their job is done.
- Preserve harness-owned files such as `AGENTS.md`, `CLAUDE.md`, `.codex/**`, `.claude/**`, and `.agents/**`; they are configuration, not managed docs.
- Preserve test fixtures exactly enough that they continue testing the intended parser, linter, and formatter behavior.
- Make frontmatter migration scriptable by defining deterministic scope, `doc_type`, ownership, consumer, lifecycle, confidence, tags, aliases, and relationship rules before changing the validation globs.
- Keep `docs/specs/**` in scope for future project-spec documents while keeping implementation plans out of scope.

## Considered Options

- Keep frontmatter scoped to `docs/adr/**` only.
- Govern every tracked Markdown file except the standard global exclusions.
- Govern only the durable documentation corpus and explicitly exclude operational, temporary, generated, harness-owned, and fixture files.

## Decision Outcome

Chosen option: "Govern only the durable documentation corpus and explicitly exclude operational, temporary, generated, harness-owned, and fixture files," because it gives the repository useful document metadata without treating every Markdown file as permanent documentation.

The durable corpus includes ADRs, specs, references, research summaries, operator/user documentation, product documentation, and hook documentation. It excludes handoff state, scratchpads, reviews, implementation plans, root work-queue/status files, agent harness files, templates, fixtures, and generated or vendored content.

This ADR records the accepted convention. It does not by itself widen `.project-standards.yml` or require existing Markdown files to change; those changes happen during the later migration task.

### Governed scope

When this ADR is approved and the migration is performed, `.project-standards.yml` should govern these Markdown paths:

```yaml
include:
  - 'docs/**/*.md'
  - 'docs/research/*.md'
  - 'products/**/*.md'
  - 'hooks/**/*.md'
```

`docs/research/*.md` is intentionally named even though `docs/**/*.md` already matches it. Research files are an explicit durable-documentation class in this repo, and the redundant include keeps that intent visible in the config.

### Excluded scope

The governed scope must exclude:

```yaml
exclude:
  - 'docs/scratchpad.md'
  - 'docs/handoff/**'
  - 'docs/reviews/**'
  - 'docs/plans/**'
  - 'docs/superpowers/plans/**'
  - 'tests/fixtures/**'
  - 'README.md'
  - 'TODO.md'
  - 'STATUS.md'
  - 'CHANGELOG.md'
  - 'CLAUDE.md'
  - 'AGENTS.md'
  - '.claude/**'
  - '.agents/**'
  - '.codex/**'
  - '.github/**'
  - 'node_modules/**'
  - '**/*.template.md'
```

The exclusions are semantic, not just a convenience:

- `docs/scratchpad.md` is a temporary working surface.
- `docs/handoff/**` is agent session state and has its own lifetime rules.
- `docs/reviews/**` holds review artifacts; reviews should be deleted after the review is complete and are not part of the durable corpus.
- `docs/plans/**` and `docs/superpowers/plans/**` hold execution plans; plans should be deleted after completion and are not part of the durable corpus.
- `tests/fixtures/**` must stay free to model valid and invalid Markdown shapes.
- Root work files such as `TODO.md` and `STATUS.md` are operational companion files, not durable documentation.
- Agent instruction/config files are harness surfaces, not managed documents.
- Template files intentionally contain placeholders that need not validate as real documents.

### Frontmatter profile

Governed files should use the standard frontmatter profile, not only the minimal required profile:

```yaml
---
schema_version: '1.1'
id: 'note-xxxxxx-human-title'
title: 'Human Title'
description: 'One-sentence description of the document.'
doc_type: 'note'
status: 'draft'
created: 'YYYY-MM-DD'
updated: 'YYYY-MM-DD'
reviewed: null
owner: 'agent-pseudocode-maintainers'
consumer: 'mix'
tags: []
aliases: []
related: []
source: []
confidence: 'unknown'
visibility: 'internal'
license: null
---
```

Relationship fields such as `supersedes`, `superseded_by`, `depends_on`, and `applies_to` should be added only when they carry real information.

### Ownership

`owner` identifies the role responsible for keeping the document correct. It is not necessarily the author, last editor, or reviewer. Use a stable role string, not a person's name, unless one person is intentionally the long-term owner.

Governed documents should have a non-empty `owner` before the widened frontmatter scope is enforced. During migration, an empty owner is allowed only as a temporary marker for documents that still need review.

Use these owner values unless a future ADR adds more:

| Owner | Use when |
| --- | --- |
| `agent-pseudocode-maintainers` | Default owner for repo-wide documentation, ADRs, specs, and cross-cutting docs. |
| `language-maintainers` | Normative language docs, APSEUDO rule references, syntax docs, and language examples. |
| `tooling-maintainers` | CLI, formatter, validator, runner, LSP, MCP, hooks, and enforcement docs. |
| `product-maintainers` | VS Code, Kate, and other product/package-specific docs. |
| `docs-maintainers` | Indexes, navigation pages, and docs-structure pages whose main job is corpus maintenance. |

If more than one role could own a document, choose the role that would decide whether a content change is correct. Put collaborating roles in the body, an ADR project extension, or review notes, not in `owner`.

### Consumers

`consumer` identifies the intended reader. Use it to decide how much operational detail, implementation detail, and agent-facing context belongs in the body.

| Consumer | Use when |
| --- | --- |
| `user` | The document is primarily for human users or contributors running the tooling. |
| `agent` | The document is primarily for LLM agents, automation, or generated workflows. |
| `mix` | Both humans and agents should rely on the document. This is the default for durable repo docs. |
| `unknown` | Only during migration or for an intentionally unclassified draft. Do not leave accepted docs as `unknown`. |

Default mapping:

| Document class | Consumer |
| --- | --- |
| ADRs, specs, references, and research | `mix` |
| Installation, usage, troubleshooting, and product docs | `user` unless the doc gives agent-specific operating instructions |
| Agent workflow docs, generated rule catalogs, and validation policy docs | `mix` |
| Machine-only prompts or automation notes, if added later | `agent` |

### Document type mapping

Use the standard `doc_type` values as follows:

| Path or document class | `doc_type` |
| --- | --- |
| `README.md`, `index.md`, and directory landing pages inside governed scope | `index` |
| `docs/adr/adr-*.md` | `adr` |
| `docs/specs/**/*.md` | `spec` |
| `docs/reference/**/*.md` and stable factual catalogs | `reference` |
| `docs/research/*.md` | `research` |
| Installation, setup, usage, and operational procedure docs | `runbook` |
| Explanatory models, mental models, and conceptual documentation | `concept` |
| Generated-schema or metadata-schema documentation, if added later | `schema` |
| Reusable prompt documents, if added later | `prompt` |
| General durable notes that do not fit a narrower type | `note` |

Do not invent new `doc_type` values. If a future document does not fit the standard enum, either classify it with the closest existing value or propose a standard change upstream.

### Status lifecycle

`status` describes whether the document should be relied on today.

| Status | Use when | State-change trigger |
| --- | --- | --- |
| `draft` | New or materially rewritten content is still being formed. | New document creation, major rewrite, or unresolved design choices. |
| `review` | The document is complete enough to inspect but should not be relied on until checked. | Stale facts suspected, large automated migration, or human review requested. |
| `active` | The document is current and usable. This is this repo's stable state. | Maintainer/operator approval, validation against current repo state, or completion of review. |
| `deprecated` | The document still exists but should not guide new work. | Replacement direction chosen, old interface documented, or content kept only for transition. |
| `superseded` | Another document replaces this document. | A replacement document exists and `superseded_by` is set. |
| `archived` | Historical record only; not expected to be maintained. | Content is intentionally retained for history but removed from the active corpus. |
| `stub` | Intentional placeholder with little or no body content. | A navigation or future-content placeholder is created and should validate without pretending to be complete. |

Status changes must be paired with metadata updates:

- Bump `updated` for meaningful content or lifecycle changes.
- Set `reviewed` only when a human maintainer/operator has actually reviewed the content for correctness.
- Add `superseded_by` when moving to `superseded`.
- Prefer deleting temporary reviews and plans over moving them through document statuses, because those paths are outside the durable corpus.

### Confidence

`confidence` describes how much trust a reader should place in the document's facts. It is not a measure of writing quality.

| Confidence | Use when | State-change trigger |
| --- | --- | --- |
| `unknown` | No confidence assessment has been made. | New scaffold, mechanical migration, or imported content not yet reviewed. |
| `low` | Content is plausible but weakly supported, stale, contradicted, or based on partial inspection. | Missing source, failed validation, stale implementation paths, or unresolved contradiction. |
| `medium` | Content is based on repo inspection, existing docs, or known project history, but has not been freshly verified end to end. | Agent review against current files, partial test evidence, or source docs that may drift. |
| `high` | Content is sourced, current, reviewed, and directly verified against code, tests, generated output, or an authoritative document. | Human correctness review, passing validation, verified generated output, or direct source-of-truth confirmation. |

Upgrade confidence only when evidence improves. Downgrade it when a related implementation changes, a source link breaks, validation fails, or a reader finds a contradiction. When in doubt during migration, choose `unknown` or `medium`, not `high`.

### Tags

Tags are retrieval labels. They should be lowercase kebab-case, specific enough to filter on, and shared across similar documents. A document may use additional tags when they are useful, but the tags below are the repo's preferred vocabulary.

Use these baseline tags by document class:

| Document class | Baseline tags |
| --- | --- |
| ADR index and ADRs | `adr`, plus one or more decision-topic tags |
| Specs | `spec`, plus feature or component tags |
| References | `reference`, plus subject tags such as `language`, `rules`, or `runner` |
| Research | `research`, plus subject tags and method/source tags when useful |
| Installation and usage docs | `usage` or `install`, plus component tags |
| Enforcement and hook docs | `enforcement`, `hooks`, plus relevant agent/tool tags |
| Product docs | `product`, plus product tags such as `vscode` or `kate` |
| Index pages | `index`, plus the section tag |

Preferred tag meanings:

| Tag | Meaning and when to use |
| --- | --- |
| `adr` | Architecture Decision Records and ADR indexes. |
| `agent-hooks` | Claude/Codex hook behavior and hook installation docs. |
| `agent-workflow` | Documents about how agents should perform tasks. |
| `ci` | Continuous-integration workflows, checks, and gate decisions. |
| `cli` | Command-line interface docs and command behavior. |
| `codex` | Codex-specific behavior or integration docs. |
| `docs` | Documentation-structure and documentation-maintenance topics. |
| `documentation` | General documentation governance, style, or metadata docs. |
| `editor-integration` | Editor integration docs that are not specific to one editor. |
| `enforcement` | Validation, hooks, pre-commit, CI, or compliance mechanics. |
| `exception` | ADRs or docs recording a deliberate deviation from a standard. |
| `formatter` | `apseudo-format` behavior or formatting policy. |
| `frontmatter` | Markdown frontmatter conventions or metadata. |
| `hooks` | Repo hook docs or hook implementation details. |
| `index` | Navigation or landing pages. |
| `install` | Installation and setup procedures. |
| `kate` | Kate editor integration. |
| `language` | Pythonic Agent Pseudocode syntax and semantics. |
| `lsp` | Language server docs and behavior. |
| `markdown` | Markdown syntax, Markdown tooling, or Markdown file governance. |
| `mcp` | MCP server docs and behavior. |
| `product` | Product/package-specific docs under `products/**`. |
| `python-tooling` | Python tooling standard, Ruff, BasedPyright, pytest, coverage, or pip-audit. |
| `reference` | Stable factual reference material. |
| `research` | Investigation summaries and durable findings. |
| `rules` | APSEUDO rule catalog or rule behavior. |
| `runner` | Executable pseudocode runner behavior. |
| `spec` | Project specs under `docs/specs/**`. |
| `standards-adoption` | Work adopting or deviating from project standards. |
| `usage` | User-facing usage docs and examples. |
| `validator` | `apseudo-lint`, validation rules, or validation APIs. |
| `vscode` | VS Code extension docs or behavior. |

Do not add synonym tags that differ only in wording. Prefer `validator` over `lint`, `editor-integration` over `editor`, and `usage` over `how-to` unless a new distinction is useful enough to define here later.

### IDs and links

Ordinary governed documents use this stable id form:

```text
{doc_type}-{base36-6}-{document-slug}
```

The first segment must match the document's `doc_type`. The six-character token must be generated by tooling or script, not invented by hand. The slug is frozen at creation time and does not change when a title or file path changes.

ADRs keep the ADR-specific id form:

```text
adr-{NNNN}-agent-pseudocode-{short-title}
```

Frontmatter relationship fields such as `related`, `source`, `supersedes`, `superseded_by`, and `depends_on` should use repository-root-relative paths with file extensions. Avoid bare IDs, bare filenames, absolute paths, and section anchors in frontmatter relationships.

Use relationship fields this way:

| Field | Add when | Reference form |
| --- | --- | --- |
| `related` | A reader would naturally consult the other document for nearby context. | Repo-root-relative path with extension. |
| `source` | The document depends on evidence, source material, code, generated output, or a standard. | Repo-root-relative path or stable external URL. |
| `supersedes` | This document replaces one or more older documents. | Repo-root-relative path when the old document remains in repo; otherwise stable id or URL. |
| `superseded_by` | This document has been replaced. | Repo-root-relative path to the replacement whenever possible. |
| `depends_on` | This document is not independently usable unless another document, standard, or artifact remains valid. | Repo-root-relative path with extension. |
| `applies_to` | The document governs a component, command, package, or path rather than another document. | Component names, command names, or repo-relative paths. |

Rules:

- Add `related` sparingly. Do not list every parent index, every child page, or every document that happens to share a tag.
- Use `source` for evidence, not for "see also" links. Code files, generated catalogs, standards docs, and external docs can be sources when they support claims in the body.
- If a document records an exception or deviation, include the governing standard or prior decision in `source` or `related`.
- If a relationship is already expressed by `supersedes`, `superseded_by`, or `depends_on`, do not duplicate the same path in `related` unless it helps retrieval.
- Body links may point to specific sections, but frontmatter relationship fields should remain document-level links.

### Aliases

`aliases` are search aids for names a reader is likely to type but that do not belong in the title. Use aliases for acronyms, command names, former titles, common abbreviations, product names, or numbered decision references.

Rules:

- Do not repeat the document title as an alias.
- Preserve normal capitalization for names and acronyms.
- Add aliases only when they improve retrieval; an empty list is better than filler.
- Add old titles as aliases when a document is renamed but still commonly known by the old name.
- For command docs, include the command names the page documents.
- For ADRs, include `ADR NNNN` and any short spoken name that differs from the title.

Common alias patterns:

| Document class         | Alias examples                                       |
| ---------------------- | ---------------------------------------------------- |
| ADRs                   | `ADR 0003`, `Frontmatter scope`                      |
| Language standard docs | `APSEUDO standard`, `Pythonic Agent Pseudocode`      |
| Rule catalog docs      | `APSEUDO rules`, `Rule catalog`                      |
| Runner docs            | `Runner spec`, `apseudo-run`                         |
| CLI usage docs         | `apseudo-lint`, `apseudo-format`, `apseudo-template` |
| MCP docs               | `MCP server`, `apseudo-mcp`                          |
| LSP docs               | `Language server`, `apseudo-lsp`                     |
| Editor product docs    | `VS Code extension`, `Kate integration`              |
| Enforcement docs       | `pre-commit hooks`, `CI gate`, `agent hooks`         |

### Migration procedure

Widening the frontmatter scope is a gated migration:

1. Confirm the existing governed scope validates cleanly.
2. Inventory all target Markdown files and classify each governed file with the mapping in this ADR.
3. Exclude temporary, operational, harness-owned, generated, vendored, and fixture files before widening config.
4. Add or repair frontmatter while `.project-standards.yml` is still narrow, so the migration diff can be reviewed before enforcement changes.
5. Review generated frontmatter for `owner`, `consumer`, `doc_type`, `status`, `tags`, `aliases`, `related`, `source`, `confidence`, and `visibility`.
6. Widen `.project-standards.yml` only after the corpus has conforming frontmatter.
7. Run the repo's Markdown fix pass and non-mutating checks, then run frontmatter validation.

The migration should be scripted as much as practical, but the script must not blindly guess semantic fields that require review.

### Consequences

- Good, because durable docs become easier for agents and humans to classify, search, validate, and relate.
- Good, because temporary reviews and plans remain easy to delete after their work is complete.
- Good, because test fixtures and harness metadata are not distorted to satisfy a documentation schema they do not belong to.
- Good, because the migration has a clear order that avoids breaking validation by widening the config before files are ready.
- Bad, because excluded files will not have standard frontmatter even when they contain useful context.
- Bad, because classifying existing docs still needs human review; a script can scaffold fields, but it cannot reliably decide trust, visibility, or lifecycle status.

### Confirmation

This decision is confirmed when:

- this ADR is accepted;
- `.project-standards.yml` includes the approved governed and excluded scopes;
- every governed Markdown file carries conformant standard-profile frontmatter;
- excluded files either carry no project-standards frontmatter or intentionally use a separate local metadata contract;
- `uv run project-standards validate --config .project-standards.yml`, or the version-pinned equivalent documented for this repo, exits `0`;
- the Markdown Tooling Standard fix pass and check contract pass.

## Pros and Cons of the Options

### Keep frontmatter scoped to docs/adr only

- Good, because it preserves today's validation behavior and avoids migration churn.
- Good, because it keeps frontmatter adoption limited to the ADR prerequisite.
- Bad, because it leaves durable reference, research, spec, product, and usage docs without consistent metadata.
- Bad, because future agents still need to infer document type and lifecycle from filenames and body text.

### Govern every tracked Markdown file

- Good, because it gives every Markdown file a uniform metadata shape.
- Good, because the config is simple to explain.
- Bad, because it treats operational files, temporary plans, reviews, scratchpads, fixtures, and harness config as if they were durable documentation.
- Bad, because it creates busywork and risks damaging files whose value depends on preserving unusual Markdown shapes.

### Govern the durable documentation corpus only

- Good, because it applies the standard where metadata improves retrieval, review, and maintenance.
- Good, because it respects the separate lifetimes of docs, handoff state, reviews, plans, fixtures, and harness config.
- Neutral, because the include and exclude lists are longer than a blanket repo-wide rule.
- Bad, because the boundary must be maintained when new documentation directories are added.

## More Information

Related standing convention: `docs/handoff/conventions.md` C-004 states that `.project-standards.yml` frontmatter scope is deliberately narrow until a separate frontmatter migration decision is made.

The selected boundary follows the general project-standards migration pattern: start from a clean baseline, define `doc_type` mapping, plan the migration, and exclude vendored, generated, temporary, operational, and fixture material before widening validation.
