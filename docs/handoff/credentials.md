# Credentials

**Last updated:** 2026-07-23

The toolkit has no runtime external-service credentials. The repository explainer video uses this build-time credential reference:

| Purpose | Environment variable | OpenBao path | Required permission |
| --- | --- | --- | --- |
| OpenAI narration | `OPENAI_API_KEY` | `secret/api-keys/ai/openai-tts` | Restricted key with Write access to Speech only |

Resolve the value at production time. Never store it in repository files, logs, captures, or generated media.
