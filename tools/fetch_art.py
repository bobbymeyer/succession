"""Fetch the card art into assets/.

The illustrations are too big to keep in git (about 1.5 MB a card), so they
live as files on the repository's `art` release:

    https://github.com/bobbymeyer/succession/releases/tag/art

This downloads each PNG there that `assets/` is missing, or holds at a
different size (a card re-painted and uploaded again), and leaves the rest:

    python tools/fetch_art.py

New or re-painted art goes onto the release -- drag the PNG onto the release's
edit page, named as `art/filenames.txt` says -- and then everyone fetches it.
Set GITHUB_TOKEN to lift the API's unauthenticated rate limit.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPO = "bobbymeyer/succession"
TAG = "art"


#: Attempts at each request: GitHub's file servers now and then answer a
#: download with a 5xx or drop it, and a second try gets it.
ATTEMPTS = 4


def _get(url: str, accept: str = "application/vnd.github+json"):
    request = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "succession-fetch-art"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        request.add_header("Authorization", f"Bearer {token}")
    for attempt in range(ATTEMPTS):
        try:
            return urllib.request.urlopen(request, timeout=120)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            # A 4xx is an answer (no such release, no such file); only a
            # server error or a dropped connection is worth another try.
            if isinstance(error, urllib.error.HTTPError) and error.code < 500:
                raise
            if attempt == ATTEMPTS - 1:
                raise
            time.sleep(2 ** attempt)


def release_assets(repo: str = REPO, tag: str = TAG) -> list[dict]:
    """The files on the release: name, size and download URL of each."""

    with _get(f"https://api.github.com/repos/{repo}/releases/tags/{tag}") as response:
        release = json.load(response)
    out: list[dict] = []
    page = 1
    while True:
        with _get(f"https://api.github.com/repos/{repo}/releases/{release['id']}/assets?per_page=100&page={page}") as response:
            batch = json.load(response)
        out.extend(batch)
        if len(batch) < 100:
            return out
        page += 1


def _download(url: str) -> bytes:
    """The file's bytes, trying again if the connection drops partway."""

    for attempt in range(ATTEMPTS):
        try:
            with _get(url, accept="application/octet-stream") as response:
                return response.read()
        except (ConnectionError, TimeoutError):
            if attempt == ATTEMPTS - 1:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def fetch(dest: Path, repo: str = REPO, tag: str = TAG, *, quiet: bool = False) -> int:
    """Download what `dest` lacks or holds stale; return how many files came down."""

    dest.mkdir(parents=True, exist_ok=True)
    fetched = 0
    for asset in sorted(release_assets(repo, tag), key=lambda a: a["name"]):
        if not asset["name"].endswith(".png"):
            continue
        path = dest / asset["name"]
        if path.exists() and path.stat().st_size == asset["size"]:
            continue
        data = _download(asset["browser_download_url"])
        path.write_bytes(data)
        fetched += 1
        if not quiet:
            print(f"fetched {asset['name']} ({len(data) // 1024} KB)")
    return fetched


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dest", type=Path, default=REPO_ROOT / "assets", help="where the art goes (default: assets/)")
    parser.add_argument("--repo", default=REPO)
    parser.add_argument("--tag", default=TAG, help="the release holding the art (default: art)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    fetched = fetch(args.dest, args.repo, args.tag, quiet=args.quiet)
    total = len(list(args.dest.glob("*.png")))
    print(f"{fetched} fetched; {total} pieces of art in {args.dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
