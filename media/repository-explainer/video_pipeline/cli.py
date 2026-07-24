"""Expose thin local orchestration for the repository explainer quick demo."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

from .captions import AI_NARRATION_DISCLOSURE, CaptionError, compile_captions
from .capture import CaptureError, verify_evidence_manifest
from .errors import ManifestError
from .manifest import load_project
from .quick_verify import DELIVERY_FILES, VerificationError, verify_delivery
from .render import RenderError, render_production
from .speech import (
    SpeechError,
    SpeechTerminalError,
    UrllibTransport,
    generate_narration,
)

EXIT_OK = 0
EXIT_CHECK_FAILED = 1
EXIT_RUNTIME = 2


class PipelineCliError(RuntimeError):
    """Report an invalid local orchestration request."""


class _Arguments(argparse.Namespace):
    command: str
    output: Path | None
    dry_run: bool
    selected_wav: Path | None


def build_parser() -> argparse.ArgumentParser:
    """Build the stable quick-demo command surface."""
    parser = argparse.ArgumentParser(description="Repository explainer video pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "capture", "narrate", "render", "verify", "all"):
        stage = subparsers.add_parser(command)
        stage.add_argument(
            "--output",
            type=Path,
            help="output root (defaults to the repository's dist/video)",
        )
        stage.add_argument(
            "--dry-run",
            action="store_true",
            help="print redacted stages and paths without writes or network access",
        )
        if command in {"render", "all"}:
            stage.add_argument(
                "--selected-wav",
                type=Path,
                help="approved narration WAV; skips Speech when used with all",
            )
    return parser


def main(argv: list[str] | None = None, *, repository_root: Path | None = None) -> int:
    """Run one quick-demo command and return a stable concise status."""
    args = build_parser().parse_args(argv, namespace=_Arguments())
    root = (repository_root or Path(__file__).parents[3]).resolve()
    try:
        output_root = _resolve_output_root(root, args.output)
        if args.dry_run:
            _print_dry_run(args.command, output_root, args.selected_wav is not None)
            return EXIT_OK
        return _run_command(args, root, output_root)
    except (
        CaptionError,
        CaptureError,
        ManifestError,
        PipelineCliError,
        RenderError,
        SpeechError,
        VerificationError,
        OSError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME


def _run_command(args: _Arguments, repository_root: Path, output_root: Path) -> int:
    if args.command == "check":
        _check_stage(repository_root, output_root)
        return EXIT_OK
    if args.command == "capture":
        _capture_stage(repository_root, output_root)
        return EXIT_OK
    if args.command == "narrate":
        _narrate_stage(repository_root, output_root)
        return EXIT_OK
    if args.command == "render":
        selected_wav = _required_selected_wav(args.selected_wav)
        _render_stage(repository_root, output_root, selected_wav)
        return EXIT_OK
    if args.command == "verify":
        return EXIT_OK if _verify_stage(repository_root, output_root) else EXIT_CHECK_FAILED
    if args.command == "all":
        _check_stage(repository_root, output_root)
        _capture_stage(repository_root, output_root)
        selected_wav = (
            _required_selected_wav(args.selected_wav)
            if args.selected_wav is not None
            else _narrate_stage(repository_root, output_root)
        )
        _render_stage(repository_root, output_root, selected_wav)
        return EXIT_OK if _verify_stage(repository_root, output_root) else EXIT_CHECK_FAILED
    raise PipelineCliError(f"unknown command: {args.command}")


def _check_stage(repository_root: Path, output_root: Path) -> None:
    production_root = repository_root / "media" / "repository-explainer"
    project = load_project(
        production_root / "project.json",
        repository_root=repository_root,
        output_root=output_root,
    )
    compiled = compile_captions(production_root / "narration.json", project)
    if compiled != (production_root / "captions.srt").read_bytes():
        raise CaptionError("captions.srt does not match narration.json")


def _capture_stage(repository_root: Path, _output_root: Path) -> None:
    verify_evidence_manifest(
        repository_root / "media" / "repository-explainer" / "captures" / "manifest.json",
        repository_root=repository_root,
    )


def _narrate_stage(repository_root: Path, output_root: Path) -> Path:
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key is None:
        raise SpeechTerminalError("OPENAI_API_KEY is unavailable through the launch wrapper")
    production_root = repository_root / "media" / "repository-explainer"
    project = load_project(
        production_root / "project.json",
        repository_root=repository_root,
        output_root=output_root,
    )
    result = generate_narration(
        narration_path=production_root / "narration.json",
        project=project,
        output_dir=output_root / "work" / "narration",
        api_key=api_key,
        transport=UrllibTransport(),
    )
    return result.selected_wav


def _render_stage(repository_root: Path, output_root: Path, selected_wav: Path) -> None:
    wav = _required_selected_wav(selected_wav)
    result = render_production(
        repository_root,
        selected_wav=wav,
        selected_wav_sha256=_sha256(wav),
    )
    final_root = output_root / "final"
    final_root.mkdir(parents=True, exist_ok=True)
    expected_narrated = final_root / DELIVERY_FILES["narrated"]
    expected_speaker = final_root / DELIVERY_FILES["speaker"]
    if result.narrated.resolve() != expected_narrated.resolve():
        raise RenderError("renderer returned a noncanonical narrated output")
    if result.speaker.resolve() != expected_speaker.resolve():
        raise RenderError("renderer returned a noncanonical speaker output")
    shutil.copyfile(
        repository_root / "media" / "repository-explainer" / "captions.srt",
        final_root / DELIVERY_FILES["captions"],
    )
    delivery = {
        "ai_narration_disclosure": AI_NARRATION_DISCLOSURE,
        "narration_captioned_variants": ["narrated"],
        "files": {
            "captions": DELIVERY_FILES["captions"],
            "narrated": DELIVERY_FILES["narrated"],
            "speaker": DELIVERY_FILES["speaker"],
        },
        "evidence_text_files": [],
    }
    (final_root / DELIVERY_FILES["delivery"]).write_text(
        json.dumps(delivery, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _verify_stage(repository_root: Path, output_root: Path) -> bool:
    report = verify_delivery(
        repository_root=repository_root,
        delivery_root=output_root / "final",
    )
    return report.passed


def _resolve_output_root(repository_root: Path, value: Path | None) -> Path:
    expected = (repository_root / "dist" / "video").resolve()
    candidate = expected if value is None else value.resolve()
    if candidate != expected:
        raise PipelineCliError(f"--output must resolve to {expected}")
    return candidate


def _required_selected_wav(value: Path | None) -> Path:
    if value is None:
        raise PipelineCliError("--selected-wav is required for render")
    path = value.resolve()
    if not path.is_file() or path.stat().st_size == 0:
        raise PipelineCliError("--selected-wav must name a nonempty file")
    return path


def _print_dry_run(command: str, output_root: Path, has_selected_wav: bool) -> None:
    stages = [command]
    if command == "all":
        stages = ["check", "capture"]
        if not has_selected_wav:
            stages.append("narrate")
        stages.extend(("render", "verify"))
    selected = "<provided>" if has_selected_wav else "<generated-below-work>"
    print(
        "dry-run "
        f"stages={','.join(stages)} "
        f"output={output_root} "
        f"work={output_root / 'work'} "
        f"selected_wav={selected}"
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
