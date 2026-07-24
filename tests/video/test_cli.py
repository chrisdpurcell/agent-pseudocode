"""Command-line orchestration contracts for the quick repository demo."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from video_pipeline import cli
from video_pipeline.errors import ManifestError
from video_pipeline.quick_verify import DELIVERY_FILES


@dataclass(frozen=True, slots=True)
class _Rendered:
    narrated: Path
    speaker: Path


def test_build_parser__commands__exposes_quick_demo_stages() -> None:
    parser = cli.build_parser()

    for command in ("check", "capture", "narrate", "render", "verify", "all"):
        parsed = parser.parse_args([command, "--dry-run"])
        assert parsed.command == command


def test_main__all_dry_run__prints_redacted_plan_without_running_stages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def unexpected(*_args: object, **_kwargs: object) -> None:
        pytest.fail("dry-run must not execute a production stage")

    for name in (
        "_check_stage",
        "_capture_stage",
        "_narrate_stage",
        "_render_stage",
        "_verify_stage",
    ):
        monkeypatch.setattr(cli, name, unexpected)

    status = cli.main(["all", "--dry-run"], repository_root=tmp_path)

    assert status == cli.EXIT_OK
    output = capsys.readouterr().out
    assert "check,capture,narrate,render,verify" in output
    assert str(tmp_path / "dist" / "video") in output
    assert str(tmp_path / "dist" / "video" / "work") in output
    assert "OPENAI_API_KEY" not in output


def test_main__stage_failure__returns_stable_runtime_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_check(_repository_root: Path, _output_root: Path) -> None:
        raise ManifestError("project manifest is invalid")

    monkeypatch.setattr(cli, "_check_stage", fail_check)

    status = cli.main(["check"], repository_root=tmp_path)

    assert status == cli.EXIT_RUNTIME
    assert capsys.readouterr().err == "error: project manifest is invalid\n"


def test_main__all_with_selected_wav__renders_without_speech(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected_wav = tmp_path / "selected.wav"
    selected_wav.write_bytes(b"RIFF diagnostic")
    calls: list[str] = []

    def record_check(_repository_root: Path, _output_root: Path) -> None:
        calls.append("check")

    def record_capture(_repository_root: Path, _output_root: Path) -> None:
        calls.append("capture")

    monkeypatch.setattr(cli, "_check_stage", record_check)
    monkeypatch.setattr(cli, "_capture_stage", record_capture)

    def unexpected_narrate(_repository_root: Path, _output_root: Path) -> Path:
        pytest.fail("a selected WAV must bypass Speech")

    monkeypatch.setattr(cli, "_narrate_stage", unexpected_narrate)

    def record_render(_repository_root: Path, _output_root: Path, wav: Path) -> None:
        assert wav == selected_wav.resolve()
        calls.append("render")

    def record_verify(_repository_root: Path, _output_root: Path) -> bool:
        calls.append("verify")
        return True

    monkeypatch.setattr(cli, "_render_stage", record_render)
    monkeypatch.setattr(cli, "_verify_stage", record_verify)

    status = cli.main(
        ["all", "--selected-wav", str(selected_wav)],
        repository_root=tmp_path,
    )

    assert status == cli.EXIT_OK
    assert calls == ["check", "capture", "render", "verify"]


def test_render_stage__selected_wav__writes_basic_delivery_inventory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    production_root = tmp_path / "media" / "repository-explainer"
    production_root.mkdir(parents=True)
    (production_root / "captions.srt").write_text("diagnostic captions\n", encoding="utf-8")
    output_root = tmp_path / "dist" / "video"
    final_root = output_root / "final"
    final_root.mkdir(parents=True)
    narrated = final_root / DELIVERY_FILES["narrated"]
    speaker = final_root / DELIVERY_FILES["speaker"]
    narrated.write_bytes(b"narrated")
    speaker.write_bytes(b"speaker")
    selected_wav = tmp_path / "selected.wav"
    selected_wav.write_bytes(b"selected")

    def fake_render(
        _root: Path,
        *,
        selected_wav: Path,
        selected_wav_sha256: str,
    ) -> _Rendered:
        assert selected_wav.is_file()
        assert len(selected_wav_sha256) == 64
        return _Rendered(narrated=narrated, speaker=speaker)

    monkeypatch.setattr(cli, "render_production", fake_render)

    status = cli.main(
        ["render", "--selected-wav", str(selected_wav)],
        repository_root=tmp_path,
    )

    assert status == cli.EXIT_OK
    assert (final_root / DELIVERY_FILES["captions"]).read_text(encoding="utf-8")
    delivery = json.loads((final_root / DELIVERY_FILES["delivery"]).read_text(encoding="utf-8"))
    assert delivery["narration_captioned_variants"] == ["narrated"]
    assert delivery["files"] == {
        "captions": DELIVERY_FILES["captions"],
        "narrated": DELIVERY_FILES["narrated"],
        "speaker": DELIVERY_FILES["speaker"],
    }


def test_main__verify_failure__returns_failed_check_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_verify(_repository_root: Path, _output_root: Path) -> bool:
        return False

    monkeypatch.setattr(cli, "_verify_stage", fail_verify)

    assert cli.main(["verify"], repository_root=tmp_path) == cli.EXIT_CHECK_FAILED
