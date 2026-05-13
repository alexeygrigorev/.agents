#!/usr/bin/env python3
"""Transcribe local audio with OpenAI without project dependencies."""

import argparse
import json
import mimetypes
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_PROMPT = (
    "Russian and English software-engineering voice notes about LiteHive. "
    "Preserve code identifiers when possible: AgentManager, Workspace, "
    "SandboxLauncher, Engine, pipeline, runtime settings, dependency injection, "
    "events, artifacts, sessions, CLI, daemon, OutcomeKind, OutcomeReasonCode."
)


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        name = name.strip().removeprefix("export ").strip()
        value = value.strip().strip('"').strip("'")
        values[name] = value
    return values


def candidate_env_files() -> list[Path]:
    root = Path("/home/alexey/git")
    if not root.exists():
        return []
    paths = []
    for pattern in (".env", ".env.local", "*.env"):
        paths.extend(root.glob(f"**/{pattern}"))
    return sorted(set(path for path in paths if path.is_file()))


def resolve_openai_config(env_file: Path | None, auto_env: bool) -> tuple[str, str]:
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    if not api_key and env_file:
        values = read_env_file(env_file)
        api_key = values.get("OPENAI_API_KEY")
        base_url = values.get("OPENAI_BASE_URL", base_url)

    if not api_key and auto_env:
        for path in candidate_env_files():
            values = read_env_file(path)
            api_key = values.get("OPENAI_API_KEY")
            if api_key:
                base_url = values.get("OPENAI_BASE_URL", base_url)
                print(f"Using OPENAI_API_KEY from {path}", file=sys.stderr)
                break

    if not api_key:
        raise SystemExit(
            "OPENAI_API_KEY is not set. Pass --env-file /path/to/.env, "
            "set the environment variable, or use --auto-env."
        )

    return api_key, base_url.rstrip("/")


def multipart_body(fields: dict[str, str], file_path: Path) -> tuple[bytes, str]:
    boundary = "----openai-transcribe-" + secrets.token_hex(16)
    chunks: list[bytes] = []

    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode(),
                b"\r\n",
            ]
        )

    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    chunks.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                'Content-Disposition: form-data; name="file"; '
                f'filename="{file_path.name}"\r\n'
            ).encode(),
            f"Content-Type: {mime_type}\r\n\r\n".encode(),
            file_path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(chunks), boundary


def transcribe(
    api_key: str,
    base_url: str,
    audio_path: Path,
    model: str,
    language: str | None,
    prompt: str | None,
) -> dict | str:
    fields = {"model": model}
    if model == "whisper-1":
        fields["response_format"] = "verbose_json"
    else:
        fields["response_format"] = "json"
    if language:
        fields["language"] = language
    if prompt:
        fields["prompt"] = prompt

    body, boundary = multipart_body(fields, audio_path)
    request = urllib.request.Request(
        f"{base_url}/audio/transcriptions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"OpenAI transcription failed for {audio_path}: {error.code} {detail}") from error

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def timestamp(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"


def split_audio(audio_path: Path, chunk_seconds: int) -> list[Path]:
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required to split audio files larger than the upload limit.")
    chunk_root = Path(tempfile.mkdtemp(prefix=f"{audio_path.stem}-chunks-"))
    pattern = chunk_root / f"{audio_path.stem}.part-%03d.m4a"
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(audio_path),
        "-f",
        "segment",
        "-segment_time",
        str(chunk_seconds),
        "-reset_timestamps",
        "1",
        "-c",
        "copy",
        str(pattern),
    ]
    subprocess.run(command, check=True)
    return sorted(chunk_root.glob(f"{audio_path.stem}.part-*.m4a"))


def combine_chunk_results(results: list[dict | str], chunk_seconds: int) -> dict:
    combined_segments = []
    combined_text = []
    for index, result in enumerate(results):
        offset = index * chunk_seconds
        if isinstance(result, str):
            text = result.strip()
            if text:
                combined_text.append(text)
            continue

        text = str(result.get("text", "")).strip()
        if text:
            combined_text.append(text)
        for segment in result.get("segments", []) or []:
            adjusted = dict(segment)
            adjusted["start"] = float(adjusted.get("start", 0)) + offset
            adjusted["end"] = float(adjusted.get("end", 0)) + offset
            combined_segments.append(adjusted)

    return {
        "text": " ".join(combined_text),
        "segments": combined_segments,
        "chunk_seconds": chunk_seconds,
        "chunk_count": len(results),
    }


def write_outputs(audio_path: Path, out_dir: Path, model: str, result: dict | str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = audio_path.stem
    safe_model = model.replace("/", "_")
    raw_path = out_dir / f"{stem}.openai-{safe_model}.json"
    text_path = out_dir / f"{stem}.openai-{safe_model}.txt"

    if isinstance(result, str):
        text_path.write_text(result, encoding="utf-8")
        print(text_path)
        return

    raw_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    segments = result.get("segments")
    if isinstance(segments, list):
        for segment in segments:
            start = float(segment.get("start", 0))
            text = str(segment.get("text", "")).strip()
            if text:
                lines.append(f"[{timestamp(start)}] {text}")
    else:
        text = str(result.get("text", "")).strip()
        if text:
            lines.append(text)

    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(raw_path)
    print(text_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", nargs="+", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--auto-env", action="store_true")
    parser.add_argument("--model", default="whisper-1")
    parser.add_argument("--language", default="ru")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--chunk-seconds", default=600, type=int)
    parser.add_argument("--upload-limit-bytes", default=24_000_000, type=int)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    api_key, base_url = resolve_openai_config(args.env_file, args.auto_env)
    for audio_path in args.audio:
        audio_path = audio_path.expanduser().resolve()
        if not audio_path.exists():
            raise SystemExit(f"Audio file not found: {audio_path}")
        if audio_path.stat().st_size > args.upload_limit_bytes:
            chunk_paths = split_audio(audio_path, args.chunk_seconds)
            print(f"Split {audio_path} into {len(chunk_paths)} chunks", file=sys.stderr)
            chunk_results = []
            for chunk_path in chunk_paths:
                chunk_results.append(transcribe(api_key, base_url, chunk_path, args.model, args.language, args.prompt))
            result = combine_chunk_results(chunk_results, args.chunk_seconds)
        else:
            result = transcribe(api_key, base_url, audio_path, args.model, args.language, args.prompt)
        out_dir = args.out_dir or audio_path.parent
        write_outputs(audio_path, out_dir, args.model, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
