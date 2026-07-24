"""Repository ownership and Git-index policy for production manifest paths."""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path

from .errors import ManifestError


def trusted_output_root(repository_root: Path, configured_root: Path | None) -> Path:
    """Return the caller-authorized output root, never a root chosen by manifest data."""
    candidate = (
        configured_root if configured_root is not None else repository_root / "dist" / "video"
    )
    resolved = _resolve(candidate, "output.root")
    if not resolved.is_relative_to(repository_root):
        raise ManifestError("output.root: trusted output root must stay inside the repository")
    return resolved


def resolve_authorized_output_root(
    value: str, repository_root: Path, authorized_root: Path
) -> Path:
    """Resolve a manifest output root only when it equals the caller-authorized root."""
    resolved = _resolve_relative(value, repository_root, "output.root")
    if resolved != authorized_root:
        raise ManifestError("output.root: must equal the trusted authorized output root")
    if not _is_git_ignored(resolved, repository_root, "output.root"):
        raise ManifestError("output.root: trusted output root must be Git-ignored")
    return resolved


def resolve_exact_output_target(
    value: str, output_root: Path, expected: Path, repository_root: Path, field: str
) -> Path:
    """Resolve one generated target and reject noncanonical or index-tracked locations."""
    resolved = _resolve_relative(value, output_root, field)
    if resolved != expected:
        raise ManifestError(f"{field}: must equal its authorized generated target")
    if _is_git_tracked(resolved, repository_root, field):
        raise ManifestError(f"{field}: generated target must not be Git-tracked")
    return resolved


def resolve_tracked_source(value: str, repository_root: Path, field: str) -> Path:
    """Resolve a source only when it is an existing regular file in the Git index."""
    resolved = _resolve_relative(value, repository_root, field)
    try:
        mode = resolved.stat().st_mode
    except FileNotFoundError as exc:
        raise ManifestError(f"{field}: source file does not exist") from exc
    except OSError as exc:
        raise ManifestError(f"{field}: source file cannot be inspected") from exc
    if not stat.S_ISREG(mode):
        raise ManifestError(f"{field}: source must be a regular file")
    if not _is_git_tracked(resolved, repository_root, field):
        raise ManifestError(f"{field}: source must be Git-tracked")
    return resolved


def _resolve_relative(value: str, root: Path, field: str) -> Path:
    candidate = Path(value)
    if (
        candidate.is_absolute()
        or not candidate.parts
        or any(part in {".", ".."} for part in candidate.parts)
    ):
        raise ManifestError(f"{field}: must be a relative path without traversal")
    resolved = _resolve(root / candidate, field)
    if not resolved.is_relative_to(root):
        raise ManifestError(f"{field}: escapes its authorized root")
    return resolved


def _resolve(path: Path, field: str) -> Path:
    try:
        return path.resolve()
    except OSError as exc:
        raise ManifestError(f"{field}: path resolution failed") from exc


def _is_git_ignored(path: Path, repository_root: Path, field: str) -> bool:
    relative = f"{path.relative_to(repository_root).as_posix()}/.video-pipeline-ignore-probe"
    return (
        _git_exit_code(
            ["check-ignore", "--quiet", "--", relative], repository_root, field, "ignore evaluation"
        )
        == 0
    )


def _is_git_tracked(path: Path, repository_root: Path, field: str) -> bool:
    relative = path.relative_to(repository_root).as_posix()
    return (
        _git_exit_code(
            ["ls-files", "--error-unmatch", "--", relative], repository_root, field, "index lookup"
        )
        == 0
    )


def _git_exit_code(args: list[str], repository_root: Path, field: str, operation: str) -> int:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repository_root,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except FileNotFoundError as exc:
        raise ManifestError(f"{field}: Git is unavailable for {operation}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ManifestError(f"{field}: Git {operation} timed out") from exc
    except OSError as exc:
        raise ManifestError(f"{field}: Git {operation} could not start") from exc
    if completed.returncode not in {0, 1}:
        raise ManifestError(f"{field}: Git {operation} failed")
    return completed.returncode
