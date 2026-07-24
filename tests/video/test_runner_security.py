"""Process-tree safety contracts for guarded runner subprocesses."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

from video_pipeline.runner_security import (
    MAX_PROCESS_OUTPUT_BYTES,
    RunnerOperationalError,
    build_child_environment,
    run_capture_process,
)

_SPAWNED_CHILD = """\
import pathlib
import subprocess
import sys
import time

child = subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(6)"],
)
pathlib.Path(sys.argv[1]).write_text(str(child.pid), encoding="utf-8")
if sys.argv[2] == "overflow":
    print("x" * (int(sys.argv[3]) + 1), flush=True)
time.sleep(6)
"""


@pytest.mark.parametrize(
    ("mode", "timeout", "reason"),
    [
        pytest.param("timeout", 1, "timed out", id="timeout"),
        pytest.param("overflow", 10, "output exceeded", id="output-overflow"),
    ],
)
def test_run_capture_process__failure__terminates_descendant_process_group(
    tmp_path: Path,
    mode: str,
    timeout: int,
    reason: str,
) -> None:
    child_pid_path = tmp_path / "child.pid"

    started_at = time.monotonic()
    with pytest.raises(RunnerOperationalError, match=reason):
        run_capture_process(
            (
                sys.executable,
                "-c",
                _SPAWNED_CHILD,
                os.fspath(child_pid_path),
                mode,
                str(MAX_PROCESS_OUTPUT_BYTES),
            ),
            cwd=tmp_path,
            environment=build_child_environment(None),
            timeout=timeout,
            operation=f"fixture {mode}",
        )

    assert time.monotonic() - started_at < 3
    child_pid = int(child_pid_path.read_text(encoding="utf-8"))
    assert not _running_process(child_pid)


def _running_process(pid: int) -> bool:
    stat_path = Path(f"/proc/{pid}/stat")
    try:
        fields = stat_path.read_text(encoding="utf-8").split()
    except FileNotFoundError:
        return False
    return len(fields) >= 3 and fields[2] != "Z"
