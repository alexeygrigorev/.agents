---
name: fetch-zoom
description: Fetch timestamped transcripts from passcode-protected Zoom shared recordings. Use when the user provides a zoom.us `/rec/share/` URL and wants its transcript.
---

# Fetch Zoom

Fetch a transcript from a Zoom shared-recording link. Prefer Zoom's existing
captions. If the recording has no captions, download the video temporarily and
transcribe its audio locally with WhisperX.

## Fetch the Transcript

Run from the directory where the transcript should be written:

```bash
uv run --python 3.13 \
  --with requests --with whisperx --with torch \
  python <skill-directory>/scripts/fetch_zoom.py \
  '<zoom-share-url>' '<passcode>' '<output.txt>'
```

Replace `<skill-directory>` with the directory that contains this `SKILL.md`.
Quote the URL and passcode because Zoom passcodes can contain shell
metacharacters. Choose an output path that is outside the target repository
unless the user explicitly wants the transcript committed.

The script prints the recording topic and duration, then writes timestamped
lines:

```text
[00:00] Welcome to the session.
[01:14] Let's look at the first example.
```

## Requirements and Behavior

- Require a public Zoom shared-recording URL and its passcode.
- Require `uv` and `ffmpeg` for recordings without Zoom captions.
- Keep downloaded video and extracted audio in a temporary directory and
  delete them when transcription finishes.
- Write only the transcript to the requested output path.
- Never place the Zoom URL, passcode, recording topic, or transcript in a
  public file unless the user explicitly asks for that content to be public.
- Stop after writing the transcript. Do not summarize or otherwise process its
  contents as part of this skill.
