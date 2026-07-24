"""Quick-demo verification contracts for media, delivery metadata, and credentials."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from video_pipeline.captions import AI_NARRATION_DISCLOSURE
from video_pipeline.quick_verify import (
    DELIVERY_FILES,
    LoudnessFacts,
    MediaFacts,
    VerificationError,
    VerificationExpectations,
    check_loudness,
    check_media,
    parse_loudness,
    parse_probe,
    verify_delivery,
)


def _run_ffmpeg(destination: Path, *, frequency: int) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x180:r=30:d=1",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={frequency}:sample_rate=48000:duration=1",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-frames:v",
            "30",
            "-c:v",
            "libopenh264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "libfdk_aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            "-y",
            os.fspath(destination),
        ],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=30,
    )


@pytest.fixture
def diagnostic_delivery(tmp_path: Path) -> tuple[Path, VerificationExpectations, tuple[Path, ...]]:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("FFmpeg and FFprobe are required for the diagnostic media fixture")

    delivery_root = tmp_path / "delivery"
    delivery_root.mkdir()
    tracked_source = tmp_path / "media" / "repository-explainer" / "source.txt"
    tracked_source.parent.mkdir(parents=True)
    tracked_source.write_text("credential reference: OPENAI_API_KEY\n", encoding="utf-8")
    subprocess.run(
        ["git", "init", "--quiet"],
        cwd=tmp_path,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    subprocess.run(
        ["git", "add", "media/repository-explainer/source.txt"],
        cwd=tmp_path,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    _run_ffmpeg(delivery_root / DELIVERY_FILES["narrated"], frequency=880)
    _run_ffmpeg(delivery_root / DELIVERY_FILES["speaker"], frequency=440)
    (delivery_root / DELIVERY_FILES["captions"]).write_text(
        "1\n00:00:00,000 --> 00:00:00,800\nDiagnostic caption.\n",
        encoding="utf-8",
    )
    (delivery_root / DELIVERY_FILES["delivery"]).write_text(
        json.dumps(
            {
                "ai_narration_disclosure": AI_NARRATION_DISCLOSURE,
                "narration_captioned_variants": ["narrated"],
                "files": {
                    "narrated": DELIVERY_FILES["narrated"],
                    "speaker": DELIVERY_FILES["speaker"],
                    "captions": DELIVERY_FILES["captions"],
                },
            }
        ),
        encoding="utf-8",
    )
    explicit_evidence = tmp_path / "production.log"
    explicit_evidence.write_text("verification completed\n", encoding="utf-8")
    expectations = VerificationExpectations.diagnostic(
        width=320,
        height=180,
        fps=30,
        frames=30,
        duration_seconds=1.0,
        narrated_lufs=-21.0,
        narrated_lufs_tolerance=20.0,
        narrated_peak_dbtp=0.0,
        speaker_lufs=-21.0,
        speaker_lufs_tolerance=20.0,
        speaker_peak_dbtp=0.0,
    )
    return delivery_root, expectations, (explicit_evidence,)


def test_parse_probe__valid_payload__returns_direct_media_facts() -> None:
    facts = parse_probe(
        {
            "format": {
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
                "duration": "135.000000",
            },
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "field_order": "progressive",
                    "avg_frame_rate": "30/1",
                    "nb_read_frames": "4050",
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "channels": 2,
                    "channel_layout": "stereo",
                },
            ],
        }
    )

    assert facts.container == "mp4"
    assert facts.video_codec == "h264"
    assert (facts.width, facts.height, facts.fps, facts.frames) == (1920, 1080, 30.0, 4050)
    assert facts.progressive is True
    assert (facts.audio_codec, facts.audio_channels) == ("aac", 2)


def test_parse_loudness__ebu_summary__returns_integrated_lufs_and_true_peak() -> None:
    facts = parse_loudness(
        """
        [Parsed_ebur128_0] Summary:

          Integrated loudness:
            I:         -16.2 LUFS

          True peak:
            Peak:       -1.4 dBFS
        """
    )

    assert facts.integrated_lufs == -16.2
    assert facts.true_peak_dbtp == -1.4


@pytest.mark.parametrize(
    ("facts", "failure"),
    [
        pytest.param(
            MediaFacts("matroska", 135.0, "h264", 1920, 1080, True, 30.0, 4050, "aac", 2, "stereo"),
            "container",
            id="container",
        ),
        pytest.param(
            MediaFacts("mp4", 135.0, "hevc", 1920, 1080, True, 30.0, 4050, "aac", 2, "stereo"),
            "video codec",
            id="video-codec",
        ),
        pytest.param(
            MediaFacts("mp4", 135.0, "h264", 1280, 720, True, 30.0, 4050, "aac", 2, "stereo"),
            "dimensions",
            id="dimensions",
        ),
        pytest.param(
            MediaFacts("mp4", 135.0, "h264", 1920, 1080, False, 30.0, 4050, "aac", 2, "stereo"),
            "progressive scan",
            id="progressive",
        ),
        pytest.param(
            MediaFacts("mp4", 135.0, "h264", 1920, 1080, True, 29.97, 4050, "aac", 2, "stereo"),
            "frame rate",
            id="frame-rate",
        ),
        pytest.param(
            MediaFacts("mp4", 135.0, "h264", 1920, 1080, True, 30.0, 4049, "aac", 2, "stereo"),
            "frame count",
            id="frame-count",
        ),
        pytest.param(
            MediaFacts("mp4", 135.04, "h264", 1920, 1080, True, 30.0, 4050, "aac", 2, "stereo"),
            "duration",
            id="duration",
        ),
        pytest.param(
            MediaFacts("mp4", 135.0, "h264", 1920, 1080, True, 30.0, 4050, "opus", 2, "stereo"),
            "audio codec",
            id="audio-codec",
        ),
        pytest.param(
            MediaFacts("mp4", 135.0, "h264", 1920, 1080, True, 30.0, 4050, "aac", 1, "mono"),
            "stereo audio",
            id="stereo",
        ),
    ],
)
def test_check_media__invalid_fact__names_failed_contract(
    facts: MediaFacts,
    failure: str,
) -> None:
    result = check_media("narrated", facts, VerificationExpectations.production())

    assert result.passed is False
    assert failure in result.detail


@pytest.mark.parametrize(
    ("facts", "passed"),
    [
        pytest.param(LoudnessFacts(-15.0, -1.0), True, id="inclusive-boundaries"),
        pytest.param(LoudnessFacts(-14.9, -1.0), False, id="loudness-high"),
        pytest.param(LoudnessFacts(-16.0, -0.9), False, id="peak-high"),
    ],
)
def test_check_loudness__production_narrated_boundaries__return_expected(
    facts: LoudnessFacts,
    passed: bool,
) -> None:
    result = check_loudness(
        "narrated",
        facts,
        VerificationExpectations.production().narrated,
    )

    assert result.passed is passed


def test_production_expectations__modified_value__is_rejected() -> None:
    modified = replace(VerificationExpectations.production(), frames=30)

    with pytest.raises(VerificationError, match="production expectations"):
        modified.validate()


def test_verify_delivery__diagnostic_fixture__passes_without_production_acceptance(
    diagnostic_delivery: tuple[Path, VerificationExpectations, tuple[Path, ...]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delivery_root, expectations, scan_paths = diagnostic_delivery
    monkeypatch.setenv("OPENAI_API_KEY", "sk-environment-value-must-never-be-read")

    report = verify_delivery(
        repository_root=delivery_root.parent,
        delivery_root=delivery_root,
        expectations=expectations,
        credential_scan_paths=scan_paths,
    )

    assert report.passed is True
    assert report.mode == "diagnostic"
    assert report.production_accepted is False
    assert set(report.sha256) == set(DELIVERY_FILES.values())
    report_text = (delivery_root / "verification-report.json").read_text(encoding="utf-8")
    assert "sk-environment-value-must-never-be-read" not in report_text


def test_verify_delivery__empty_captions__fails_file_and_hash_checks(
    diagnostic_delivery: tuple[Path, VerificationExpectations, tuple[Path, ...]],
) -> None:
    delivery_root, expectations, scan_paths = diagnostic_delivery
    (delivery_root / DELIVERY_FILES["captions"]).write_bytes(b"")

    report = verify_delivery(
        repository_root=delivery_root.parent,
        delivery_root=delivery_root,
        expectations=expectations,
        credential_scan_paths=scan_paths,
    )

    failed = {check.name for check in report.checks if not check.passed}
    assert {"captions_file", "sha256_inventory"} <= failed


def test_verify_delivery__missing_disclosure__fails_delivery_metadata(
    diagnostic_delivery: tuple[Path, VerificationExpectations, tuple[Path, ...]],
) -> None:
    delivery_root, expectations, scan_paths = diagnostic_delivery
    delivery_path = delivery_root / DELIVERY_FILES["delivery"]
    delivery = json.loads(delivery_path.read_text(encoding="utf-8"))
    delivery["ai_narration_disclosure"] = ""
    delivery_path.write_text(json.dumps(delivery), encoding="utf-8")

    report = verify_delivery(
        repository_root=delivery_root.parent,
        delivery_root=delivery_root,
        expectations=expectations,
        credential_scan_paths=scan_paths,
    )

    assert any(check.name == "delivery_metadata" and not check.passed for check in report.checks)


def test_verify_delivery__credential_in_explicit_log__fails_targeted_scan(
    diagnostic_delivery: tuple[Path, VerificationExpectations, tuple[Path, ...]],
) -> None:
    delivery_root, expectations, _ = diagnostic_delivery
    production_log = delivery_root.parent / "production.log"
    production_log.write_text("Authorization: Bearer sk-test-secret-value\n", encoding="utf-8")

    report = verify_delivery(
        repository_root=delivery_root.parent,
        delivery_root=delivery_root,
        expectations=expectations,
        credential_scan_paths=(production_log,),
    )

    assert report.passed is False
    assert any(check.name == "credential_scan" and not check.passed for check in report.checks)


def test_verify_delivery__explicit_log__still_scans_tracked_media_source(
    diagnostic_delivery: tuple[Path, VerificationExpectations, tuple[Path, ...]],
) -> None:
    delivery_root, expectations, scan_paths = diagnostic_delivery
    tracked_source = delivery_root.parent / "media" / "repository-explainer" / "source.txt"
    tracked_source.write_text("api_key = sk-tracked-secret-value\n", encoding="utf-8")

    report = verify_delivery(
        repository_root=delivery_root.parent,
        delivery_root=delivery_root,
        expectations=expectations,
        credential_scan_paths=scan_paths,
    )

    assert report.passed is False
    assert any(
        check.name == "credential_scan"
        and not check.passed
        and "media/repository-explainer/source.txt" in check.detail
        for check in report.checks
    )
