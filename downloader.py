#!/usr/bin/env python3
"""Simple URL downloader script used by the web app.

Usage:
    python downloader.py <url> <output_dir>
"""

from __future__ import annotations

import pathlib
import sys
import urllib.parse
import urllib.request


def _safe_filename_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    name = pathlib.Path(parsed.path).name or "downloaded_file"
    return name


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python downloader.py <url> <output_dir>", file=sys.stderr)
        return 1

    url = sys.argv[1]
    output_dir = pathlib.Path(sys.argv[2]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = _safe_filename_from_url(url)
    destination = output_dir / filename

    with urllib.request.urlopen(url) as response:
        destination.write_bytes(response.read())

    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
