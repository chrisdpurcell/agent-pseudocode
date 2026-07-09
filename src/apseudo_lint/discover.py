"""Git-aware path discovery for hooks and apseudo-lint --changed."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .extract import collect_paths
from .model import LintConfig


def discover_changed_paths(config: LintConfig) -> list[Path]:
    """Return Git-changed lintable files relative to the current repository."""

    root = git_root() or Path.cwd()
    files: set[Path] = set()
    commands = [
        ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB", "HEAD", "--"],
        ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB", "--cached", "--"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    for command in commands:
        try:
            result = subprocess.run(
                command,
                cwd=root,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            continue
        if result.returncode not in (0, 1):
            continue
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            path = root / stripped
            if path.exists() and path.is_file():
                files.update(collect_paths([path], config))
    return sorted(files, key=lambda item: str(item))


def git_root() -> Path | None:
    """Return the current Git repository root, if available."""

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    root = result.stdout.strip()
    return Path(root) if root else None
