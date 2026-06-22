---
name: openai-transcribe
description: Transcribe local audio files with the OpenAI Audio Transcriptions API without adding OpenAI dependencies to the target project.
allowed-tools: Bash(python *)
argument-hint: [audio-file ...]
---

# OpenAI Transcribe

Use `scripts/transcribe.py` to transcribe local audio through the
OpenAI Audio Transcriptions API.

The script intentionally uses only the Python standard library. It
does not add `openai` or any other dependency to the repository being
worked on.

## Authentication

The script reads the API key in this order:

1. `OPENAI_API_KEY` from the current environment.
2. `--env-file /path/to/.env`, reading `OPENAI_API_KEY=...`.
3. `--auto-env`, scanning local project `.env` files under
   `/home/alexey/git` and using the first file that contains
   `OPENAI_API_KEY`.

The key is never printed.

## Example

```bash
python /home/alexey/git/.agents/skills/openai-transcribe/scripts/transcribe.py \
  --auto-env \
  --model whisper-1 \
  --language ru \
  --out-dir docs/source-recordings \
  docs/source-recordings/example.m4a
```

For `whisper-1`, the script requests `verbose_json` and writes both
the raw JSON response and a timestamped `.txt` file.

Files larger than the OpenAI upload limit are split with `ffmpeg`
before transcription, then combined back into one timestamped output.
