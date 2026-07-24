"""Behavior contracts for promotion-blocking video verification."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import cast

import pytest

from video_pipeline.models import MediaSettings, Rectangle, VisualState
from video_pipeline.scenes import ContentReference, RenderedSceneState


def _probe_payload(*, frames: int = 4050, duration: str = "135.000000") -> dict[str, object]:
    return {
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "h264",
                "profile": "High",
                "width": 1920,
                "height": 1080,
                "pix_fmt": "yuv420p",
                "r_frame_rate": "30/1",
                "duration": duration,
                "nb_read_frames": str(frames),
            },
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac",
                "profile": "LD",
                "sample_rate": "48000",
                "channels": 2,
                "duration": duration,
            },
        ],
        "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": duration},
        "program_audio_boundary": {
            "first_program_sample": 0,
            "last_program_sample_exclusive": 6_480_000,
            "packet_after_program_boundary": False,
        },
    }


def _loudness(integrated: float, peak: float) -> str:
    return f"""
[Parsed_ebur128_0 @ 0x1] Summary:

  Integrated loudness:
    I:         {integrated:.1f} LUFS

  Loudness range:
    LRA:         1.2 LU

  True peak:
    Peak:       {peak:.1f} dBFS
"""


def _state(
    state_id: str,
    start: int,
    end: int,
    *,
    scene_id: str = "scene",
    evidence: tuple[Rectangle, ...] = (),
    display_text: str = "Visible meaning",
    asset_ids: tuple[str, ...] = ("font",),
) -> RenderedSceneState:
    svg = f"<svg><text>{display_text}</text></svg>".encode()
    return RenderedSceneState(
        scene_id=scene_id,
        state_id=state_id,
        start_frame=start,
        end_frame=end,
        svg=svg,
        evidence_rectangles=evidence,
        essential_rectangles=(Rectangle(5, 5, 80, 40),),
        copy_rectangle=Rectangle(5, 5, 80, 40) if state_id == "mute_safe_copy" else None,
        caption_rectangle=Rectangle(5, 80, 90, 15),
        display_text=display_text,
        content_ledger=(display_text,),
        references=(
            ContentReference(
                kind="source",
                path="source.txt",
                sha256=hashlib.sha256(b"source").hexdigest(),
                revision=None,
            ),
        ),
        asset_ids=asset_ids,
    )


def test_tc_t8_001__probe_and_loudness_parsers__emit_explicit_variant_rows() -> None:
    from video_pipeline.verify import parse_ebur128, verify_media_variant

    media = MediaSettings(width=1920, height=1080, fps=30, total_frames=4050)
    narrated = verify_media_variant(
        "narrated",
        _probe_payload(),
        parse_ebur128(_loudness(-16.0, -1.2)),
        media=media,
    )
    speaker = verify_media_variant(
        "speaker",
        _probe_payload(),
        parse_ebur128(_loudness(-28.0, -6.2)),
        media=media,
    )

    assert [row.id for row in narrated] == [
        "MEDIA-narrated-format",
        "MEDIA-narrated-streams",
        "MEDIA-narrated-duration",
        "AUDIO-narrated-loudness",
        "AUDIO-narrated-peak",
    ]
    assert [row.id for row in speaker] == [
        "MEDIA-speaker-format",
        "MEDIA-speaker-streams",
        "MEDIA-speaker-duration",
        "AUDIO-speaker-loudness",
        "AUDIO-speaker-peak",
    ]
    assert all(row.status == "pass" and row.evidence for row in (*narrated, *speaker))
    assert narrated[3].evidence["measured_lufs"] == -16.0
    assert speaker[3].evidence["measured_lufs"] == -28.0


@pytest.mark.parametrize(
    ("variant", "integrated", "peak", "failed_id"),
    [
        pytest.param("narrated", -14.9, -1.2, "AUDIO-narrated-loudness", id="narrated-loud"),
        pytest.param("narrated", -16.0, -0.9, "AUDIO-narrated-peak", id="narrated-peak"),
        pytest.param("speaker", -25.9, -6.2, "AUDIO-speaker-loudness", id="speaker-loud"),
        pytest.param("speaker", -28.0, -5.9, "AUDIO-speaker-peak", id="speaker-peak"),
    ],
)
def test_tc_t8_001__variant_audio_boundaries__fail_the_exact_row(
    variant: str, integrated: float, peak: float, failed_id: str
) -> None:
    from video_pipeline.verify import VariantName, parse_ebur128, verify_media_variant

    rows = verify_media_variant(
        cast(VariantName, variant),
        _probe_payload(),
        parse_ebur128(_loudness(integrated, peak)),
        media=MediaSettings(width=1920, height=1080, fps=30, total_frames=4050),
    )

    assert [row.id for row in rows if row.status == "fail"] == [failed_id]


def test_tc_t8_001__probe_parser__rejects_inexact_frame_and_audio_boundaries() -> None:
    from video_pipeline.verify import parse_ebur128, verify_media_variant

    probe = _probe_payload(frames=4049, duration="134.966667")
    cast(dict[str, object], probe["program_audio_boundary"])["last_program_sample_exclusive"] = (
        6_478_400
    )
    rows = verify_media_variant(
        "narrated",
        probe,
        parse_ebur128(_loudness(-16.0, -1.2)),
        media=MediaSettings(width=1920, height=1080, fps=30, total_frames=4050),
    )

    duration = next(row for row in rows if row.id == "MEDIA-narrated-duration")
    assert duration.status == "fail"
    assert duration.evidence["expected_frames"] == 4050
    assert duration.evidence["decoded_frames"] == 4049
    assert duration.evidence["expected_audio_samples"] == 6_480_000


def test_tc_t8_002__must_gate_aggregation__blocks_every_corrupted_fixture() -> None:
    from video_pipeline.verify import GateResult, aggregate_report

    passing = GateResult("MEDIA-narrated-format", "pass", {"codec": "h264"})
    for gate_id in (
        "AUTH-evidence",
        "DISCLOSURE-delivery",
        "CAPTION-speaker",
        "ACCESS-mute-safe",
        "FRAME-final-layout",
        "RIGHTS-assets",
        "AUDIO-procedural-only",
        "AUDIO-speaker-speech",
        "SECURITY-secrets",
        "REPRO-exact",
    ):
        report = aggregate_report(
            (
                passing,
                GateResult(gate_id, "fail", {"reason": "deliberately corrupted fixture"}),
            )
        )
        assert report.promotable is False
        assert report.failed_gate_ids == (gate_id,)


def test_tc_t8_002__content_gates__report_structured_failures(tmp_path: Path) -> None:
    from video_pipeline.verify import FrameReview, verify_content_contracts

    source = tmp_path / "source.txt"
    source.write_bytes(b"altered")
    states = (
        _state("main", 0, 60, asset_ids=("unclassified",)),
        _state("not-mute-safe", 60, 120),
    )
    reviews = (
        FrameReview(
            variant="narrated",
            frame=59,
            scene_id="scene",
            state_id="main",
            minimum_text_size=31,
            within_title_safe=False,
            minimum_contrast=4.49,
            narration_caption_present=True,
        ),
        FrameReview(
            variant="speaker",
            frame=59,
            scene_id="scene",
            state_id="main",
            minimum_text_size=31,
            within_title_safe=False,
            minimum_contrast=4.49,
            narration_caption_present=True,
        ),
    )
    rows = verify_content_contracts(
        repository_root=tmp_path,
        states=states,
        classified_asset_ids=frozenset({"font"}),
        delivery={"ai_narration_disclosure": ""},
        external_music_inputs=("track.mp3",),
        speaker_speech_detected=True,
        frame_reviews=reviews,
        required_frame_samples=(("narrated", 59, "scene", "main"),),
        secret_artifacts={"delivery.json": "OPENAI_API_KEY=sk-fixture-secret"},
    )
    failures = {row.id: row.evidence for row in rows if row.status == "fail"}

    assert {
        "AUTH-evidence",
        "DISCLOSURE-delivery",
        "CAPTION-speaker",
        "ACCESS-mute-safe",
        "FRAME-final-layout",
        "RIGHTS-assets",
        "AUDIO-procedural-only",
        "AUDIO-speaker-speech",
        "SECURITY-secrets",
    } <= failures.keys()
    assert failures["SECURITY-secrets"]["findings"] == [
        {"artifact": "delivery.json", "classification": "credential-assignment"}
    ]
    assert "sk-fixture-secret" not in json.dumps(failures)


def test_tc_t8_003__exact_reproduction__matches_semantics_but_ignores_container_hash() -> None:
    from video_pipeline.verify import semantic_manifest_sha256, verify_reproduction

    approved = _semantic_manifest()
    reproduced = copy.deepcopy(approved)
    cast(dict[str, object], cast(dict[str, object], reproduced["outputs"])["narrated"])[
        "sha256"
    ] = "f" * 64
    actual_toolchain = copy.deepcopy(cast(dict[str, object], approved["toolchain"]))

    row = verify_reproduction(
        approved,
        reproduced,
        actual_toolchain=actual_toolchain,
        clean_checkout=True,
        speech_api_calls=0,
    )

    assert row.status == "pass"
    assert semantic_manifest_sha256(approved) == semantic_manifest_sha256(reproduced)
    assert row.evidence["container_metadata_excluded"] is True


def test_tc_t8_003__toolchain_or_decoded_hash_mismatch__blocks_without_threshold() -> None:
    from video_pipeline.verify import verify_reproduction

    approved = _semantic_manifest()
    mismatched_toolchain = copy.deepcopy(cast(dict[str, object], approved["toolchain"]))
    cast(dict[str, object], mismatched_toolchain["ffmpeg"])["version"] = "8.1.3"
    toolchain_row = verify_reproduction(
        approved,
        approved,
        actual_toolchain=mismatched_toolchain,
        clean_checkout=True,
        speech_api_calls=0,
    )
    reproduced = copy.deepcopy(approved)
    cast(dict[str, object], cast(dict[str, object], reproduced["outputs"])["speaker"])[
        "decoded_pcm_sha256"
    ] = "9" * 64
    decoded_row = verify_reproduction(
        approved,
        reproduced,
        actual_toolchain=cast(dict[str, object], approved["toolchain"]),
        clean_checkout=True,
        speech_api_calls=0,
    )

    assert toolchain_row.status == "fail"
    assert toolchain_row.evidence["reason"] == "toolchain-mismatch"
    assert decoded_row.status == "fail"
    assert decoded_row.evidence["comparison"] == "exact-hash"
    assert "threshold" not in json.dumps(decoded_row.evidence)


def test_tc_t8_002__strict_manifest_and_asset_ledger__reject_tampering(tmp_path: Path) -> None:
    from video_pipeline.verify import verify_asset_provenance, verify_render_manifest

    source = tmp_path / "source.txt"
    source.write_bytes(b"source")
    asset = tmp_path / "asset.bin"
    asset.write_bytes(b"altered")
    state = _state("mute_safe_copy", 0, 60)
    media = MediaSettings(width=100, height=100, fps=20, total_frames=60)
    manifest = _render_manifest_for_states((state,), media)
    timing = cast(dict[str, object], manifest["project_timing"])
    record = cast(dict[str, object], cast(list[object], timing["states"])[0])
    record["source_sha256"] = "0" * 64
    provenance = {
        "schema_version": 1,
        "assets": [
            {
                "id": "asset",
                "kind": "graphic",
                "repository_path": "asset.bin",
                "system_path": None,
                "source": "Fixture",
                "license_id": None,
                "generation_method": None,
                "sha256": hashlib.sha256(b"original").hexdigest(),
            }
        ],
    }

    manifest_row = verify_render_manifest(manifest, media=media, states=(state,))
    rights_row, _ = verify_asset_provenance(provenance, repository_root=tmp_path)

    assert manifest_row.status == "fail"
    assert any(
        finding["field"] == "project_timing.states[0].source_sha256"
        for finding in cast(list[dict[str, object]], manifest_row.evidence["findings"])
    )
    assert rights_row.status == "fail"
    rights_findings = cast(list[dict[str, object]], rights_row.evidence["findings"])
    assert {finding["reason"] for finding in rights_findings} == {
        "checksum-mismatch",
        "unclassified-rights",
    }


@pytest.mark.parametrize(
    ("dominant_frames", "expected_status"),
    [
        pytest.param(59, "fail", id="below"),
        pytest.param(60, "pass", id="inclusive-lower"),
        pytest.param(80, "pass", id="inclusive-upper"),
        pytest.param(81, "fail", id="above"),
    ],
)
def test_tc_t8_004__renderer_geometry_frame_share__uses_inclusive_boundaries(
    dominant_frames: int, expected_status: str
) -> None:
    from video_pipeline.verify import verify_evidence_frame_share

    states = (
        VisualState(
            id="dominant",
            start_frame=0,
            end_frame=dominant_frames,
            evidence_rectangles=(
                Rectangle(0, 0, 60, 100),
                Rectangle(40, 0, 60, 100),
            ),
        ),
        VisualState(
            id="designed",
            start_frame=dominant_frames,
            end_frame=100,
            evidence_rectangles=(Rectangle(0, 0, 49, 100),),
        ),
    )

    row = verify_evidence_frame_share(states, width=100, height=100, total_frames=100)

    assert row.status == expected_status
    assert row.evidence["dominant_frames"] == dominant_frames
    assert row.evidence["percentage"] == dominant_frames


def test_tc_t8_001__real_short_fixture__is_probed_by_the_verifier(tmp_path: Path) -> None:
    from video_pipeline.verify import LoudnessMeasurement, probe_media_file, verify_media_variant

    output = tmp_path / "fixture.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=160x90:r=30:d=1",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=1",
            "-frames:v",
            "30",
            "-c:v",
            "libopenh264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "libfdk_aac",
            "-profile:a",
            "aac_ld",
            "-frame_length",
            "480",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(output),
        ],
        check=True,
        timeout=30,
    )
    probe = probe_media_file(output)
    rows = verify_media_variant(
        "speaker",
        probe,
        # This test exercises the real media probe; loudness parsing is covered independently.
        loudness=LoudnessMeasurement(-28.0, -6.0),
        media=MediaSettings(width=160, height=90, fps=30, total_frames=30),
    )

    assert all(row.status == "pass" for row in rows[:3])


def test_tc_t8_002__single_verifier__writes_promotable_report_and_checksums(
    tmp_path: Path,
) -> None:
    from video_pipeline.verify import (
        FrameReview,
        LoudnessMeasurement,
        VerificationInputs,
        verify_delivery,
        write_verification_report,
    )

    source = tmp_path / "source.txt"
    source.write_bytes(b"source")
    mute_state = _state(
        "mute_safe_copy",
        0,
        60,
        scene_id="promise",
        evidence=(Rectangle(0, 0, 60, 100),),
        display_text="Visible meaning. AI-generated narration.",
    )
    designed_state = _state(
        "end-card",
        60,
        100,
        scene_id="promise",
        evidence=(Rectangle(0, 0, 49, 100),),
        display_text="Visible meaning. AI-generated narration.",
    )
    states = (mute_state, designed_state)
    media = MediaSettings(width=100, height=100, fps=20, total_frames=100)
    manifest = _render_manifest_for_states(states, media)
    asset = tmp_path / "font.bin"
    asset.write_bytes(b"font")
    assets = {
        "schema_version": 1,
        "assets": [
            {
                "id": "font",
                "kind": "font",
                "repository_path": "font.bin",
                "system_path": None,
                "source": "Fixture font",
                "license_id": "OFL-1.1",
                "generation_method": None,
                "sha256": hashlib.sha256(b"font").hexdigest(),
            }
        ],
    }
    probe = _probe_payload(frames=100, duration="5.000000")
    video = cast(dict[str, object], cast(list[object], probe["streams"])[0])
    video.update({"width": 100, "height": 100, "r_frame_rate": "20/1"})
    cast(dict[str, object], probe["program_audio_boundary"])["last_program_sample_exclusive"] = (
        240_000
    )
    reviews = (
        FrameReview("narrated", 59, "promise", "mute_safe_copy", 44, True, 7.0, True),
        FrameReview("speaker", 59, "promise", "mute_safe_copy", 32, True, 7.0, False),
        FrameReview("narrated", 99, "promise", "end-card", 44, True, 7.0, True),
        FrameReview("speaker", 99, "promise", "end-card", 32, True, 7.0, False),
    )
    report = verify_delivery(
        VerificationInputs(
            repository_root=tmp_path,
            media=media,
            states=states,
            render_manifest=manifest,
            reproduced_manifest=copy.deepcopy(manifest),
            actual_toolchain=cast(dict[str, object], manifest["toolchain"]),
            probes={"narrated": probe, "speaker": copy.deepcopy(probe)},
            loudness={
                "narrated": LoudnessMeasurement(-16.0, -1.2),
                "speaker": LoudnessMeasurement(-28.0, -6.2),
            },
            asset_provenance=assets,
            delivery={"ai_narration_disclosure": "AI-generated narration."},
            frame_reviews=reviews,
            required_frame_samples=(
                ("narrated", 99, "promise", "end-card"),
                ("speaker", 99, "promise", "end-card"),
            ),
            speaker_speech_detected=False,
            clean_checkout=True,
            speech_api_calls=0,
            secret_artifacts={"delivery.json": "AI-generated narration."},
            deliverables={"source.txt": source},
        )
    )
    report_path = tmp_path / "verification-report.json"
    write_verification_report(report_path, report)
    written = json.loads(report_path.read_text(encoding="utf-8"))

    assert report.promotable is True
    assert written["promotable"] is True
    assert written["checksums"]["source.txt"] == hashlib.sha256(b"source").hexdigest()
    assert all(row["evidence"] for row in written["gates"])


def _semantic_manifest() -> dict[str, object]:
    speaker = {
        "path": "dist/video/final/output.mp4",
        "inputs": ["shared_picture", "procedural_tonal_bed_and_cues"],
        "sha256": "a" * 64,
        "decoded_video_sha256": "b" * 64,
        "decoded_pcm_sha256": "c" * 64,
        "decoded_audio_samples_per_channel": 6_480_000,
        "probe": _probe_payload(),
    }
    narrated = copy.deepcopy(speaker)
    narrated["inputs"] = [
        "shared_picture",
        "captions_srt",
        "selected_narration_wav",
        "procedural_tonal_bed_and_cues",
    ]
    return {
        "schema_version": 1,
        "source_revision": "d" * 40,
        "project_timing": {"total_frames": 4050},
        "inputs": {
            "project_contract": {"sha256": "2" * 64},
            "captions_srt": {"path": "captions.srt", "sha256": "e" * 64},
            "selected_narration_wav": {
                "path": "selected.wav",
                "sha256": "3" * 64,
                "provider_required_for_reproduction": False,
            },
            "render_recipe": {"path": "render.py", "sha256": "4" * 64},
        },
        "synthesis": {"external_music_inputs": []},
        "audio_targets": {
            "narrated": {"integrated_lufs": -16, "true_peak_dbtp": -1},
            "speaker": {"integrated_lufs": -28, "true_peak_dbtp": -6},
        },
        "toolchain": {"ffmpeg": {"version": "8.1.2", "sha256": "f" * 64}},
        "shared_picture": {"decoded_video_sha256": "b" * 64, "sha256": "1" * 64},
        "outputs": {"narrated": narrated, "speaker": speaker},
    }


def _render_manifest_for_states(
    states: tuple[RenderedSceneState, ...], media: MediaSettings
) -> dict[str, object]:
    manifest = _semantic_manifest()
    manifest["project_timing"] = {
        "width": media.width,
        "height": media.height,
        "fps": media.fps,
        "total_frames": media.total_frames,
        "total_audio_samples": round(media.total_frames / media.fps * 48_000),
        "scenes": [{"id": "scene", "start_frame": 0, "end_frame": media.total_frames}],
        "states": [
            {
                "scene_id": state.scene_id,
                "state_id": state.state_id,
                "start_frame": state.start_frame,
                "end_frame": state.end_frame,
                "frame_count": state.end_frame - state.start_frame,
                "source_sha256": state.digest,
                "cache_key": "0" * 64,
                "clip_sha256": "1" * 64,
                "references": [
                    {
                        "kind": reference.kind,
                        "path": reference.path,
                        "sha256": reference.sha256,
                        "revision": reference.revision,
                    }
                    for reference in state.references
                ],
            }
            for state in states
        ],
    }
    for output in cast(dict[str, dict[str, object]], manifest["outputs"]).values():
        output["decoded_audio_samples_per_channel"] = round(media.total_frames / media.fps * 48_000)
    return manifest
