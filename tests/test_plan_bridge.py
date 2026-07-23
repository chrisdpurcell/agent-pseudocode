import subprocess
import sys
from pathlib import Path

PLAN_SCRIPT = Path(__file__).parents[1] / "scripts" / "plan.py"


def test_generate__notes_template__separates_markdown_headings(tmp_path: Path) -> None:
    master = tmp_path / "demo-plan.md"
    master.write_text(
        """\
---
title: 'Demo Plan'
slug: 'demo'
size: standard
status: active
source: 'test'
spec_ref: ''
created: 2026-07-23
updated: 2026-07-23
owners:
  - 'Test'
test_framework: pytest
---

# Demo Plan

## Phase P1: Demo

### T1: Demo task

- **depends_on:** []
- **requirements:** [REQ-001]
- **T1.1 RED** — demonstrate the generated notes contract.
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(PLAN_SCRIPT), "generate", str(master)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    notes = (tmp_path / ".project-pipeline" / "demo" / "notes.md").read_text(encoding="utf-8")
    assert "\n\n## Deviations from the plan\n\n## Dead ends\n\n## Decisions\n\n" in notes
