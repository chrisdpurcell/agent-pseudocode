---
schema_version: '1.1'
id: 'index-49vak4-repository-explainer-video'
title: 'Repository Explainer Video'
description: 'Commands for checking, rendering, and verifying the local repository explainer video.'
doc_type: 'index'
status: 'active'
created: '2026-07-24'
updated: '2026-07-24'
tags: []
aliases: []
related:
  - 'docs/specs/repository-explainer-video.md'
---

# Repository Explainer Video

This directory contains the tracked sources for the 135-second repository explainer. Generated media stays under the repository's ignored `dist/video/` tree; all transient files stay under `dist/video/work/`.

## Prerequisites

Run the pipeline through the repository's `uv` environment. Production rendering also requires the FFmpeg, encoder, font, and library versions checked by `video_pipeline.render`.

Narration uses `OPENAI_API_KEY` from the OpenBao-backed Codex launch wrapper. The pipeline never prints the value. The existing permission smoke is a separate, explicit preproduction operation: `narrate` and `all` do not run provider denial probes.

## Check the production inputs

From the repository root, run:

```bash
uv run --project ../.. --directory media/repository-explainer python -m video_pipeline check
```

To inspect the planned stages and repository-owned paths without writes or network access:

```bash
uv run --project ../.. --directory media/repository-explainer python -m video_pipeline all --dry-run
```

## Rerender the demo

The verified selected narration WAV is retained in the final delivery. Run capture validation, rendering, and quick-demo verification without another Speech request:

```bash
uv run --project ../.. --directory media/repository-explainer python -m video_pipeline all --selected-wav ../../dist/video/final/agent-pseudocode-explainer-narration-selected.wav
```

The selected WAV must be an existing nonempty file. `all --selected-wav` skips the narration stage completely.

Individual stages use the same command form:

```bash
uv run --project ../.. --directory media/repository-explainer python -m video_pipeline capture
uv run --project ../.. --directory media/repository-explainer python -m video_pipeline render --selected-wav ../../dist/video/final/agent-pseudocode-explainer-narration-selected.wav
uv run --project ../.. --directory media/repository-explainer python -m video_pipeline verify
```

The separate `narrate` stage retains the dormant permission-smoke and three-take hardening controls for a future owner-approved narration series. It is not part of the quick rerender path.

`verify` runs the quick-demo checks and writes `dist/video/final/verification-report.json`. It directly checks both MP4s with FFprobe, including the standard AAC-LC audio profile, measures EBU R128 loudness, validates the narrated-only caption inventory and AI-narration disclosure, scans targeted text for credential patterns, and records SHA-256 hashes.

The complete local delivery is `dist/video/final/`. It contains the narrated and speaker MP4s, selected narration WAV, captions, delivery and render manifests, verification report, and `checksums.sha256`. Verify the package from that directory with `sha256sum -c checksums.sha256`.

Exit status `0` means the requested stage passed, `1` means verification completed with a failed check, and `2` means invocation or stage execution failed.
