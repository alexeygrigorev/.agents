#!/usr/bin/env python3
"""Fetch public Google Recorder audio and optionally transcribe it with WhisperX."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def read_url(url: str, data: bytes | None = None, headers: dict[str, str] | None = None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req) as res:
        return res.read(), dict(res.headers), res.status


def read_ranged_url(url: str, chunk_size: int = 8 * 1024 * 1024) -> tuple[bytes, dict[str, str]]:
    """Read downloads whose server only returns one range-sized chunk by default."""
    first_chunk, headers, status = read_url(url, headers={"Range": f"bytes=0-{chunk_size - 1}"})
    content_range = headers.get("Content-Range")
    if status != 206 or not content_range:
        return first_chunk, headers

    match = re.search(r"/(\d+)$", content_range)
    if not match:
        return first_chunk, headers
    total_size = int(match.group(1))

    chunks = [first_chunk]
    offset = len(first_chunk)
    while offset < total_size:
        end = min(offset + chunk_size - 1, total_size - 1)
        chunk, _, _ = read_url(url, headers={"Range": f"bytes={offset}-{end}"})
        chunks.append(chunk)
        offset += len(chunk)
        if not chunk:
            raise RuntimeError(f"download stopped before {total_size} bytes")
    return b"".join(chunks), headers


def safe_name(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "audio"


def extract_share_id(url: str) -> str:
    match = re.search(r"recorder\.google\.com/([0-9a-f-]{36})", url)
    if not match:
        raise ValueError("Could not find a Google Recorder share ID in the URL.")
    return match.group(1)


def get_client_config() -> dict:
    raw, _, _ = read_url("https://recorder.google.com/clientconfig")
    text = raw.decode("utf-8")
    if text.startswith(")]}'"):
        text = text.split("\n", 1)[1]
    return json.loads(text)


def rpc_call(rpc_base: str, api_key: str, method: str, share_id: str):
    url = (
        f"{rpc_base}/$rpc/java.com.google.wireless.android.pixel.recorder.protos."
        f"PlaybackService/{method}?key={urllib.parse.quote(api_key)}"
    )
    body = json.dumps([share_id]).encode("utf-8")
    headers = {
        "content-type": "application/json+protobuf",
        "origin": "https://recorder.google.com",
        "referer": "https://recorder.google.com/",
    }
    raw, _, _ = read_url(url, body, headers)
    return json.loads(raw.decode("utf-8")), raw


def fetch_recording(recorder_url: str, out_dir: Path) -> Path:
    share_id = extract_share_id(recorder_url)
    out_dir.mkdir(parents=True, exist_ok=True)

    config = get_client_config()
    api_key = config["apiKey"]
    rpc_base = config["firstPartyApiUrl"]
    download_base = config["fileDownloadUrl"]

    info, _ = rpc_call(rpc_base, api_key, "GetRecordingInfo", share_id)
    title = "google_recorder_" + safe_name(info[0][1] if info and info[0] else share_id)

    audio_url = f"{download_base}/download/playback/{share_id}"
    audio_raw, audio_headers = read_ranged_url(audio_url)
    audio_ext = ".m4a" if "audio/mp4" in audio_headers.get("Content-Type", "") else ".audio"
    audio_path = out_dir / f"{title}{audio_ext}"
    audio_path.write_bytes(audio_raw)

    try:
        transcript, transcript_raw = rpc_call(rpc_base, api_key, "GetTranscription", share_id)
        (out_dir / f"{title}.transcription.jsonpb").write_bytes(transcript_raw)
        write_recorder_transcript(transcript, out_dir / f"{title}.transcript.txt")
        write_word_timings(transcript, out_dir / f"{title}.words.json")
    except Exception as exc:
        print(f"Warning: audio fetched, but Recorder transcript fetch failed: {exc}", file=sys.stderr)

    print(audio_path)
    return audio_path


def write_recorder_transcript(transcript, path: Path) -> None:
    lines = []
    for segment in transcript[0] if transcript else []:
        rendered = ""
        for word in segment[0] or []:
            text = str(word[1] if word[1] is not None else word[0])
            rendered += ("\n" + text[1:]) if text.startswith("\n") else ((" " if rendered else "") + text)
        lines.extend(part.strip() for part in rendered.splitlines() if part.strip())
    path.write_text("\n".join(lines), encoding="utf-8")


def write_word_timings(transcript, path: Path) -> None:
    words = []
    for segment in transcript[0] if transcript else []:
        for word in segment[0] or []:
            words.append({
                "word": word[0],
                "rendered": word[1],
                "start_ms": int(word[2]),
                "end_ms": int(word[3]),
            })
    path.write_text(json.dumps(words, indent=2), encoding="utf-8")


def timestamp(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"


def transcribe_audio(
    audio_path: Path,
    model_name: str,
    device: str,
    compute_type: str,
    write_raw: bool,
) -> Path:
    try:
        import whisperx
    except ImportError as exc:
        raise SystemExit(
            "WhisperX is not installed. Run with: "
            "uv run --python 3.13 --with whisperx --with torch python recorder.py transcribe <audio>"
        ) from exc

    audio_path = audio_path.expanduser().resolve()
    if not audio_path.exists():
        raise SystemExit(f"Audio file not found: {audio_path}")

    timestamped_path = audio_path.with_suffix(".whisperx.txt")
    raw_path = audio_path.with_suffix(".whisperx.raw.txt")

    print("Loading model...")
    model = whisperx.load_model(model_name, device, compute_type=compute_type)
    print(f"Transcribing {audio_path}...")
    audio = whisperx.load_audio(str(audio_path))
    result = model.transcribe(audio)
    print(f"Done! Segments: {len(result['segments'])}, Language: {result['language']}")

    with timestamped_path.open("w", encoding="utf-8") as f:
        for segment in result["segments"]:
            f.write(f"[{timestamp(segment['start'])}] {segment['text'].strip()}\n")

    if write_raw:
        raw_path.write_text(
            " ".join(segment["text"].strip() for segment in result["segments"]),
            encoding="utf-8",
        )

    print(timestamped_path)
    if write_raw:
        print(raw_path)
    return timestamped_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch", help="Fetch original .m4a audio from a public Recorder link.")
    fetch.add_argument("url")
    fetch.add_argument("--out-dir", default=".", type=Path)

    transcribe = subparsers.add_parser("transcribe", help="Transcribe an existing audio file with WhisperX.")
    transcribe.add_argument("audio", type=Path)
    add_transcribe_options(transcribe)

    both = subparsers.add_parser("fetch-transcribe", help="Fetch audio, then transcribe it with WhisperX.")
    both.add_argument("url")
    both.add_argument("--out-dir", default=".", type=Path)
    add_transcribe_options(both)

    return parser


def add_transcribe_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default="base")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--raw", action="store_true", help="Also write a plain raw transcript file.")


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "fetch":
        fetch_recording(args.url, args.out_dir)
    elif args.command == "transcribe":
        transcribe_audio(args.audio, args.model, args.device, args.compute_type, args.raw)
    elif args.command == "fetch-transcribe":
        audio_path = fetch_recording(args.url, args.out_dir)
        transcribe_audio(audio_path, args.model, args.device, args.compute_type, args.raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
