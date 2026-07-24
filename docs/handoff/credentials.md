# Credentials

**Last updated:** 2026-07-23

The toolkit has no runtime external-service credentials. The repository explainer video uses this build-time credential reference:

| Purpose | Environment variable | OpenBao path | Required permission |
| --- | --- | --- | --- |
| OpenAI narration | `OPENAI_API_KEY` | `secret/api-keys/ai/openai-tts` | Narrowest available Restricted permission that permits Speech requests; set every separately configurable management, files, fine-tuning, assistants, and administration permission to None |

The provider may bundle Speech with other model capabilities. Record the exact dashboard bundle at production time; the production process still calls only `/v1/audio/speech`. Resolve the value at production time. Never store it in repository files, logs, captures, or generated media.
