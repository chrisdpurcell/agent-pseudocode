---
bug_id: '007'
date: '2026-07-24'
title: 'Explainer AAC-LD audio plays as static in ordinary media players'
services: [video]
status: fixed
---

## Cause

The explainer renderer explicitly selected the FDK AAC low-delay profile (`aac_ld`) so its 480-sample frames divided both approved timelines exactly. FFmpeg could decode the delivered audio, but AAC-LD is a specialist low-delay profile that ordinary MP4 players do not consistently support. An affected player reproduced the stream mostly as static even though the selected narration WAV was intact.

FFprobe confirmed both delivered MP4s used the `LD` profile. A controlled transcode of the same stream to standard AAC-LC reproduced the narration normally and preserved the picture stream, duration, loudness, and program audio.

## Fix

Applied 2026-07-24: changed the renderer to FDK AAC-LC (`aac_low`) with its standard 1024-sample frames and MP4 edit-list priming. Packet timing still has to end exactly at the program boundary; decoded semantic hashing explicitly trims the codec's final partial-frame padding to that same boundary.

The renderer tests now require an FFprobe `LC` profile, 2048-sample encoder priming, exact final packet timing, and no manual `frame_length` override. The quick-demo verifier also rejects any audio profile other than AAC-LC so the incompatible delivery cannot pass again.

Both final MP4s were rerendered from the retained selected `marin` WAV. No new provider request or narration generation was needed.

## Lesson

An MP4 containing an AAC stream is not sufficient evidence of broad player compatibility; the AAC object profile matters. Quick delivery verification must check the FFprobe profile, not only the codec name, channel count, and container.
