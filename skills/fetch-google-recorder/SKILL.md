---
name: fetch-google-recorder
description: Fetch and transcribe Google Recorder voice notes. Use when the user shares a recorder.google.com link and wants the original audio file, a transcript, or wants to act on a voice note.
allowed-tools: Bash(uv run *), Bash(python *)
argument-hint: [recorder-url]
---

# Fetch Google Recorder

Fetch Recorder-provided transcripts from public Google Recorder share
links. Fetch audio only when explicitly needed, and optionally transcribe
audio with WhisperX.

## Requirements

Google Recorder links must be public. Private links redirect to Google sign-in and cannot be fetched without an authenticated browser session or cookies.

## Fetch Recorder Transcript

Prefer this when the user asks for the transcript. Google Recorder
shares already expose a transcript through the Recorder playback RPC, so
there is no need to download the `.m4a` or run WhisperX.

Run from the directory where outputs should be written:

```bash
uv run python ~/.claude/skills/fetch-google-recorder/recorder.py transcript \
  'https://recorder.google.com/<share-id>' \
  --out-dir fetched
```

This writes:

```text
<recording-title>.transcript.txt
<recording-title>.transcription.jsonpb
<recording-title>.words.json
```

Use `.transcript.txt` for normal text workflows. Use `.words.json` only
when word-level timestamps are needed.

## Fetch Audio

Run from the directory where outputs should be written:

```bash
uv run python ~/.claude/skills/fetch-google-recorder/recorder.py fetch \
  'https://recorder.google.com/<share-id>' \
  --out-dir fetched
```

This writes the original `.m4a` audio file. The filename is lowercase and
underscore-separated, based on the Recorder title. It also tries to write
the Recorder-provided transcript files.

## Transcribe Audio

WhisperX currently needs Python 3.13 for the available Torch wheels. Use `--python 3.13` even if the surrounding repo defaults to another Python version:

```bash
uv run --python 3.13 --with whisperx --with torch \
  python ~/.claude/skills/fetch-google-recorder/recorder.py transcribe \
  fetched/google_recorder_apr_24_at_12_26.m4a
```

This writes:

```text
<audio-stem>.whisperx.txt
```

The timestamped transcript format is:

```text
[MM:SS] transcript text
```

Add `--raw` only if a plain raw transcript is also needed:

```text
<audio-stem>.whisperx.raw.txt
```

## Fetch And Transcribe

For the full flow:

```bash
uv run --python 3.13 --with whisperx --with torch \
  python ~/.claude/skills/fetch-google-recorder/recorder.py fetch-transcribe \
  'https://recorder.google.com/<share-id>' \
  --out-dir fetched
```

## Output Use

For transcript requests, use the `transcript` command first. It is faster
and avoids downloading audio.

After fetching/transcribing audio, use the `.m4a` for audio workflows and
`.whisperx.txt` for WhisperX text workflows. If WhisperX transcription
quality is poor, inspect the Recorder-provided `.transcript.txt`.
