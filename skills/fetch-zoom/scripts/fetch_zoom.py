#!/usr/bin/env python3
"""Fetch a timestamped transcript from a Zoom shared recording.

Use Zoom's captions when available. Otherwise, download the recording into a
temporary directory and transcribe its audio locally with WhisperX.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests


def base_url(share_url: str) -> str:
    parsed = urlparse(share_url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Zoom share URL must be an HTTPS URL")
    if parsed.hostname != "zoom.us" and not parsed.hostname.endswith(".zoom.us"):
        raise ValueError("Zoom share URL must use a zoom.us host")
    return f"https://{parsed.netloc}"


def share_id(share_url: str) -> str:
    parsed = urlparse(share_url)
    match = re.fullmatch(r"/rec/share/([^/]+)", parsed.path.rstrip("/"))
    if not match:
        raise ValueError("Zoom URL must contain /rec/share/<share-id>")
    return match.group(1)


def create_session(base: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Referer": f"{base}/",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
            ),
        }
    )
    return session


def extract_field(html: str, field: str) -> str | None:
    patterns = (
        rf"\b{re.escape(field)}\s*:\s*'([^']*)'",
        rf'\b{re.escape(field)}\s*:\s*"([^"]*)"',
    )
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    return None


def csrf_token(session: requests.Session, base: str) -> str:
    response = session.post(
        f"{base}/csrf_js?t_x_zm_rid=1",
        headers={"fetch-csrf-token": "1"},
        timeout=30,
    )
    response.raise_for_status()
    if ":" not in response.text:
        raise RuntimeError("Zoom returned an unexpected CSRF response")
    return response.text.split(":", 1)[1].strip()


def require_success(payload: dict, operation: str) -> dict:
    if not payload.get("status"):
        message = payload.get("errorMessage") or payload.get("errorCode") or payload
        raise RuntimeError(f"Zoom {operation} failed: {message}")
    return payload.get("result") or {}


def validate_passcode(
    session: requests.Session,
    base: str,
    meeting_id: str,
    passcode: str,
) -> None:
    headers = {"zoom-csrftoken": csrf_token(session, base)}
    response = session.post(
        f"{base}/nws/recording/1.0/validate-context",
        headers=headers,
        data={
            "meetingId": meeting_id,
            "fileId": "",
            "useWhichPasswd": "meeting",
            "sharelevel": "meeting",
            "iet": "",
        },
        timeout=30,
    )
    context = require_success(response.json(), "context validation")

    endpoint = (
        "validate-meeting-passwd"
        if context.get("useWhichPasswd") == "meeting"
        else "validate-passwd"
    )
    response = session.post(
        f"{base}/nws/recording/1.0/{endpoint}",
        headers=headers,
        data={
            "id": context["encryptMeetId"],
            "passwd": passcode,
            "action": "viewdetailpage",
            "recaptcha": "",
        },
        timeout=30,
    )
    require_success(response.json(), "passcode validation")


def recording_info(
    session: requests.Session,
    base: str,
    meeting_id: str,
) -> dict:
    response = session.get(
        f"{base}/nws/recording/1.0/play/share-info/{meeting_id}",
        params={"accessLevel": "meeting"},
        timeout=30,
    )
    redirect = require_success(response.json(), "share lookup").get("redirectUrl")
    if not redirect:
        raise RuntimeError("Zoom did not return a recording page")

    play_page = session.get(f"{base}{redirect}", timeout=30)
    play_page.raise_for_status()
    file_id = extract_field(play_page.text, "fileId")
    if not file_id:
        raise RuntimeError("Could not find the recording file ID")

    response = session.get(
        f"{base}/nws/recording/1.0/play/info/{file_id}",
        params={
            "accessLevel": "meeting",
            "canPlayFromShare": "true",
            "from": "share_recording_detail",
            "continueMode": "true",
            "componentName": "rec-play",
        },
        timeout=30,
    )
    return require_success(response.json(), "recording lookup")


def timestamp(seconds: float) -> str:
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def vtt_to_text(vtt: str) -> str:
    rendered: list[str] = []
    for block in re.split(r"\r?\n\s*\r?\n", vtt.strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing_index = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None:
            continue
        start = lines[timing_index].split("-->", 1)[0].strip().replace(",", ".")
        match = re.match(r"(?:(\d+):)?(\d{2}):(\d{2})(?:\.\d+)?$", start)
        if not match:
            continue
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        text = " ".join(lines[timing_index + 1 :])
        text = re.sub(r"<[^>]+>", "", text).strip()
        if text:
            rendered.append(
                f"[{timestamp(hours * 3600 + minutes * 60 + seconds)}] {text}"
            )
    return "\n".join(rendered)


def zoom_transcript(
    session: requests.Session,
    base: str,
    info: dict,
) -> str | None:
    transcript_url = info.get("transcriptUrl") or info.get("ccUrl")
    if not transcript_url or not info.get("hasTranscript"):
        return None
    response = session.get(f"{base}{transcript_url}", timeout=60)
    response.raise_for_status()
    transcript = vtt_to_text(response.text)
    if not transcript:
        raise RuntimeError("Zoom captions were present but could not be parsed")
    return transcript


def local_transcript(
    session: requests.Session,
    media_url: str,
    model_name: str,
) -> str:
    try:
        import whisperx
    except ImportError as exc:
        raise RuntimeError(
            "WhisperX is required because this recording has no Zoom captions"
        ) from exc

    with tempfile.TemporaryDirectory(prefix="fetch-zoom-") as temp_dir:
        video_path = Path(temp_dir) / "recording.mp4"
        audio_path = Path(temp_dir) / "audio.mp3"

        print("Downloading recording temporarily...", file=sys.stderr)
        response = session.get(
            media_url,
            stream=True,
            headers={"Range": "bytes=0-"},
            timeout=(30, 300),
        )
        response.raise_for_status()
        with video_path.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)

        print("Extracting audio...", file=sys.stderr)
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-loglevel",
                    "error",
                    "-i",
                    str(video_path),
                    "-vn",
                    "-acodec",
                    "libmp3lame",
                    "-ab",
                    "64k",
                    "-y",
                    str(audio_path),
                ],
                check=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("ffmpeg is required for local transcription") from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError("ffmpeg could not extract the recording audio") from exc

        print(
            f"Transcribing locally with WhisperX model {model_name}...", file=sys.stderr
        )
        model = whisperx.load_model(model_name, "cpu", compute_type="int8")
        audio = whisperx.load_audio(str(audio_path))
        result = model.transcribe(audio)
        return "\n".join(
            f"[{timestamp(segment['start'])}] {segment['text'].strip()}"
            for segment in result["segments"]
            if segment["text"].strip()
        )


def fetch_transcript(
    share_url: str, passcode: str, model_name: str
) -> tuple[str, int, str]:
    base = base_url(share_url)
    session = create_session(base)
    response = session.get(f"{base}/rec/share/{share_id(share_url)}", timeout=30)
    response.raise_for_status()
    meeting_id = extract_field(response.text, "meetingId")
    if not meeting_id:
        raise RuntimeError("Could not find the meeting ID on the Zoom share page")

    validate_passcode(session, base, meeting_id, passcode)
    info = recording_info(session, base, meeting_id)
    topic = info.get("meet", {}).get("topic", "Zoom recording")
    duration = int(info.get("duration") or 0)

    transcript = zoom_transcript(session, base, info)
    if transcript is None:
        media_url = info.get("mp4Url") or info.get("viewMp4Url")
        if not media_url:
            raise RuntimeError("Recording has no captions or downloadable media")
        transcript = local_transcript(session, media_url, model_name)
    return topic, duration, transcript


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("share_url", help="Zoom /rec/share/ URL")
    parser.add_argument("passcode", help="recording passcode")
    parser.add_argument("output", type=Path, help="transcript output path")
    parser.add_argument(
        "--model",
        default="base",
        help="WhisperX model for recordings without captions (default: base)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        topic, duration, transcript = fetch_transcript(
            args.share_url,
            args.passcode,
            args.model,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(transcript.rstrip() + "\n", encoding="utf-8")
    except (requests.RequestException, KeyError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Topic: {topic}")
    print(f"Duration: {duration // 60}m {duration % 60}s")
    print(f"Transcript: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
