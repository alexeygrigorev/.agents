---
name: youtube-manager
description: >
  Manage the DataTalksClub YouTube channel with the local youtube-manager-agent
  (auth, playlists, titles/descriptions, chapters, rename after Studio upload).
  Use when the user asks to update a YouTube description or title, fix video
  links, add a video to a playlist, publish chopped course clips, add chapters,
  or mentions youtube-manager-agent / YouTube Studio metadata. Use fetch-youtube
  instead for transcripts. Use when the user runs /youtube-manager.
---

# YouTube manager

Channel writes go through `~/git/youtube-manager-agent` and the YouTube Data API.
That repo is the source of truth for CLI flags, chopping, and manifests — read
its README (and `docs/chopping.md` when cutting recordings). This skill is the
agent workflow: auth, then the smallest API change that does the job.

Do **not** use this for transcripts/captions. Use **fetch-youtube**.

## Setup

Always run from the agent repo with `uv`:

```bash
cd ~/git/youtube-manager-agent
uv run python -m auth.reauth --check
```

Expect `status: VALID` and `authorized as: DataTalksClub`. Credentials live in
the gitignored `.youtube/` folder (`client_secret.json`, `token.json`). Never
commit them, print them, or copy them into the skill.

If `--check` reports `DEAD` / `invalid_grant`, stop. Ask the user to re-consent
on a machine with a browser:

```bash
cd ~/git/youtube-manager-agent
uv run python -m auth.reauth
```

Then they can drop the fresh `token.json` at `.youtube/token.json` (or
`bash bin/push_token.sh` to a remote checkout). Do not start
`run_local_server` headless.

## Course video links

DataTalks.Club course videos must link the **current** GitHub repo, not the old
bookcamp tree:

- Lesson / notebook / repo URLs: `https://github.com/DataTalksClub/<course-repo>/...`
- Machine Learning Zoomcamp files live at repo root on `main`, not under
  `course-zoomcamp/`.
- Do **not** restore stubs in `alexeygrigorev/mlbookcamp-code` to un-404 an old
  YouTube URL. Rewrite the description.

Typical ML Zoomcamp rewrite:

| Old | New |
| --- | --- |
| `https://github.com/alexeygrigorev/mlbookcamp-code/blob/master/course-zoomcamp` | `https://github.com/DataTalksClub/machine-learning-zoomcamp/blob/main` |
| `https://github.com/alexeygrigorev/mlbookcamp-code/tree/master/course-zoomcamp` | `https://github.com/DataTalksClub/machine-learning-zoomcamp` |

Verify rewritten GitHub URLs return 200 before telling the user it is done.

ML Zoomcamp playlist: `PL3MmuxUbc_hIhxl5Ji8t4O6lPAOpHaCLR`.

## Commands

```bash
cd ~/git/youtube-manager-agent

uv run python -m playlist.list_playlist PLxxxxxxxx
uv run python -m playlist.add_to_playlist --playlist PLxxxxxxxx [--position N] [--before-title "…"] [--dry-run] <id-or-url>…

uv run python -m video.rename --manifest manifests/<name>.json --dry-run
uv run python -m video.rename --manifest manifests/<name>.json

uv run python -m video.add_chapters --manifest manifests/<name>.json --chapters-dir work/chapters --dry-run
```

Playlist positions are 0-based. `add_to_playlist` is idempotent: without
`--position` it skips videos already in the playlist; with `--position` it
moves them.

**Publish chopped clips** with manual Studio upload + `video.rename`, not
`video.upload`. API `videos.insert` stays private until the Google Cloud
project is audited.

Chopping pipeline (download → spec → `bin/chop.sh` → captions/chapters): see
`docs/chopping.md`. Pull source transcripts with **fetch-youtube**.

## Read or rewrite descriptions

There is no description-only CLI. Use `videos.list` / `videos.update` via
`auth.auth.get_service`. `videos.update` with `part=snippet` **must** send
`title`, `categoryId`, and `description`. Keep existing `tags` and
`defaultLanguage` when present.

Quota: `videos.update` ≈ 50 units, `videos.insert` ≈ 1,600, default daily cap
10,000. Dry-run bulk edits (print id + title, count matches) and apply only
after the user would accept the replacement.

```python
from auth.auth import get_service

yt = get_service()
vid = "xxxxxxxxxxx"
sn = yt.videos().list(part="snippet", id=vid).execute()["items"][0]["snippet"]
new_desc = sn["description"].replace(OLD, NEW)
body = {
    "id": vid,
    "snippet": {
        "title": sn["title"],
        "description": new_desc,
        "categoryId": sn.get("categoryId", "27"),
    },
}
if sn.get("tags"):
    body["snippet"]["tags"] = sn["tags"]
if sn.get("defaultLanguage"):
    body["snippet"]["defaultLanguage"] = sn["defaultLanguage"]
yt.videos().update(part="snippet", body=body).execute()
```

For a playlist, page `playlistItems.list`, then `videos.list` in batches of 50.

After a write, fetch the snippet again and confirm the new text (and that old
prefixes are gone).
