---
name: fetch-youtube
description: Fetch YouTube video transcripts. Use when the user asks to get a YouTube video transcript, subtitles, or captions, or wants to analyze/summarize a YouTube video.
allowed-tools: Bash(uv run *)
argument-hint: [video-url-or-id]
---

# Fetch YouTube Transcript

Fetch the transcript/subtitles of a YouTube video as timestamped text.

## Efficient workflow (read this first)

The script **caches** every transcript to `~/.cache/youtube_transcripts/<video-id>.txt` and
is idempotent. So fetch **once**, then work from the file. Do **not**:

- run the command twice (once to preview, once to save) — it's already on disk,
- pipe the transcript into a second `/tmp` copy — the cache file *is* your copy,
- dump a long transcript through `head`/`cat` into context just to peek at it.

**Recommended:** use `--path` to fetch+cache and get back only the file path, then use the
`Read` tool (with `offset`/`limit` for long videos) or `grep` on that file:

```bash
uv run --with youtube-transcript-api --with python-dotenv \
  ~/.claude/skills/fetch-youtube/youtube.py <video-id-or-url> --path
```

This prints the cache path to stdout (e.g. `~/.cache/youtube_transcripts/dQw4w9WgXcQ.txt`)
and a `fetched: <path> (<N> lines)` status line to stderr — **without** sending the whole
transcript through bash. Then `Read` that file. For a short video you can read it whole; for a
long one, read in chunks or `grep` for the topic the user cares about.

**Only stream the transcript to stdout** when you genuinely need it inline and it's short:

```bash
uv run --with youtube-transcript-api --with python-dotenv \
  ~/.claude/skills/fetch-youtube/youtube.py <video-id-or-url>
```

The script accepts a video ID (`dQw4w9WgXcQ`), a full URL
(`https://www.youtube.com/watch?v=dQw4w9WgXcQ`), or a short URL (`https://youtu.be/dQw4w9WgXcQ`).

## Output format

Timestamped subtitles, one line per cue:

```
0:00 Hello and welcome
0:05 Today we're going to talk about...
1:23:45 And that wraps up our discussion
```

## Fetching a playlist

Get all video IDs and titles from a playlist (tab-separated `id<TAB>title`):

```bash
python3 ~/.claude/skills/fetch-youtube/playlist.py <playlist-id-or-url>
```

Note: only the first page (~100 videos) is returned; longer playlists need pagination support added.

## Proxy support (if YouTube blocks your IP)

The script auto-loads proxy credentials from `~/.config/youtube/.env` and passes the
configured proxy to `YouTubeTranscriptApi` — no extra flags. A safe tracked template is
[`youtube.env.example`](youtube.env.example). Copy it to the local config path, replace
placeholders locally, and keep the file private:

```bash
mkdir -p ~/.config/youtube
cp youtube.env.example ~/.config/youtube/.env
chmod 600 ~/.config/youtube/.env
```

DataImpulse uses the `login:password@hostname:port` format shown in its dashboard:

```dotenv
DATAIMPULSE_USER=your-dataimpulse-login
DATAIMPULSE_PASSWORD=your-dataimpulse-password
DATAIMPULSE_ENDPOINT=gw.dataimpulse.com:823
```

`DATAIMPULSE_HOST` and `DATAIMPULSE_PORT` may be used instead of
`DATAIMPULSE_ENDPOINT`; the defaults are `gw.dataimpulse.com` and `823`.

Oxylabs remains supported as a fallback:

```dotenv
OXYLABS_USER=...
OXYLABS_ENDPOINT=...
OXYLABS_PASSWORD=...
```

When both providers are configured, DataImpulse takes precedence. If DataImpulse is not
configured, the existing Oxylabs settings are used. Environment variables already exported
in the shell are not overwritten by the dotenv file.

Security boundary: the real credentials belong only in `~/.config/youtube/.env`, which is a
machine-local ignored file and should remain mode `600`. Never put real values in this skill,
the example file, repository files, shell history, logs, or chat. The downloader constructs
the proxy URL in memory and does not print it.

## After fetching

Proceed with what the user asked (summarize, extract key points, answer questions, make notes).
If they only said "get the transcript," tell them where it is and ask what they'd like next.
