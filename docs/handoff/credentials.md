# Credentials

**Last updated:** 2026-07-23

The toolkit has no runtime external-service credentials. The repository explainer video uses this build-time credential reference:

| Purpose | Environment variable | OpenBao path | Required permission |
| --- | --- | --- | --- |
| OpenAI narration | `OPENAI_API_KEY` | `secret/api-keys/ai/openai-tts` | Restricted key with permission to request the approved Speech model |

The production process calls only `/v1/audio/speech`. Denial probes against unrelated APIs are optional future hardening and are not part of the quick-demo delivery. Resolve the value at production time. Never store it in repository files, logs, captures, or generated media.
