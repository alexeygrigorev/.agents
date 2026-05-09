#!/usr/bin/env python3
"""Fetch all video IDs and titles from a YouTube playlist."""

import json
import re
import sys
from urllib.request import urlopen, Request


def fetch_playlist(playlist_id: str) -> list[dict[str, str]]:
    url = f"https://www.youtube.com/playlist?list={playlist_id}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urlopen(req).read().decode("utf-8")

    match = re.search(r"var ytInitialData = ({.*?});", html)
    if not match:
        print("Could not find playlist data in page", file=sys.stderr)
        sys.exit(1)

    data = json.loads(match.group(1))
    tabs = data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"]

    videos = []
    for tab in tabs:
        if "tabRenderer" not in tab or not tab["tabRenderer"].get("selected"):
            continue
        content = tab["tabRenderer"]["content"]
        sections = content["sectionListRenderer"]["contents"]
        for section in sections:
            items = section.get("itemSectionRenderer", {}).get("contents", [])
            for item in items:
                playlist = item.get("playlistVideoListRenderer", {})
                for v in playlist.get("contents", []):
                    vr = v.get("playlistVideoRenderer", {})
                    vid = vr.get("videoId", "")
                    title = vr.get("title", {}).get("runs", [{}])[0].get("text", "")
                    if vid:
                        videos.append({"id": vid, "title": title})
    return videos


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python playlist.py <playlist-id-or-url>", file=sys.stderr)
        sys.exit(1)

    arg = sys.argv[1]
    match = re.search(r"[?&]list=([a-zA-Z0-9_-]+)", arg)
    playlist_id = match.group(1) if match else arg

    videos = fetch_playlist(playlist_id)
    for v in videos:
        print(f"{v['id']}\t{v['title']}")
