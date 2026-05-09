---
name: fetch-youtube
description: Fetch YouTube video transcripts. Use when the user asks to get a YouTube video transcript, subtitles, or captions, or wants to analyze/summarize a YouTube video.
allowed-tools: Bash(uv run *)
argument-hint: [video-url-or-id]
---

# Fetch YouTube Transcript

Fetch the transcript/subtitles of a YouTube video and return it as timestamped text.

## Fetching a playlist

To get all video IDs and titles from a playlist:

```bash
python3 ~/.claude/skills/fetch-youtube/playlist.py <playlist-id-or-url>
```

Example:

```bash
python3 ~/.claude/skills/fetch-youtube/playlist.py PL3MmuxUbc_hIB4fSqLy_0AfTjVLpgjV3R
```

Output (tab-separated: video ID and title):

```
FgnelhEJFj0	LLM Zoomcamp 2025 Launch Stream
Q75JgLEXMsM	LLM Zoomcamp 1.1 – Einführung in LLM und RAG
...
```

Note: this only fetches the first page of results (typically the first ~100 videos). For longer playlists with pagination, the script would need to be extended.

## Fetching a single video transcript

## Requirements

Ensure `youtube-transcript-api` is installed:

```bash
pip install youtube-transcript-api
```

**Alternative - No installation required (using uv):**

```bash
uv run --with youtube-transcript-api python ~/.claude/skills/fetch-youtube/youtube.py <video-id-or-url>
```

## Usage

Run the fetch script with a YouTube video ID or URL:

```bash
uv run --with youtube-transcript-api --with python-dotenv ~/.claude/skills/fetch-youtube/youtube.py <video-id-or-url>
```

The script accepts either:
- A video ID: `dQw4w9WgXcQ`
- A full URL: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
- A short URL: `https://youtu.be/dQw4w9WgXcQ`

## Proxy support (if YouTube blocks your IP)

The script automatically loads Oxylabs proxy credentials from `~/.config/youtube/.env` if present. If the direct request fails, the retry will use the proxy. No extra flags needed - just run the same command above.

The `.env` file should contain:
```
OXYLABS_USER=...
OXYLABS_ENDPOINT=...
OXYLABS_PASSWORD=...
```

## Output

The script prints the transcript as timestamped subtitles to stdout:

```
0:00 Hello and welcome
0:05 Today we're going to talk about...
1:23:45 And that wraps up our discussion
```

## What to do with the output

After fetching the transcript, ask the user what they'd like to do with it. Common tasks:
- Summarize the video
- Extract key points or action items
- Answer questions about the video content
- Search for specific topics mentioned
- Create notes from the video
