#!/usr/bin/env python3
"""Simple URL downloader script used by the web app.

Usage:
    python downloader.py [-a] <url-or-file> <output_dir>

Use -a to run the optional conversion flow after download, or to convert an existing local file.
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import urllib.parse
import urllib.request


def _safe_filename_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    name = pathlib.Path(parsed.path).name or "downloaded_file"
    return name


def _convert_file(source: pathlib.Path, output_dir: pathlib.Path) -> pathlib.Path:
    """Placeholder conversion hook for deployments that replace this script.

    The web app passes ``-a`` when conversion is requested. In this sample script the
    conversion creates a copy with ``.converted`` before the original suffix, so the
    feature can be exercised without external tools. Replace this function with your
    real conversion implementation if needed.
    """
    destination = output_dir / f"{source.stem}.converted{source.suffix}"
    shutil.copy2(source, destination)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Download a URL or convert a file into an output directory.")
    parser.add_argument("-a", "--convert", action="store_true", help="convert the resulting or existing file")
    parser.add_argument("source", help="URL to download, or local file path when using -a")
    parser.add_argument("output_dir", help="directory where the result is written")
    args = parser.parse_args()

    output_dir = pathlib.Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source_path = pathlib.Path(args.source)
    if args.convert and source_path.exists():
        print(_convert_file(source_path.resolve(), output_dir))
        return 0

    filename = _safe_filename_from_url(args.source)
    destination = output_dir / filename

    with urllib.request.urlopen(args.source) as response:
        destination.write_bytes(response.read())

    if args.convert:
        destination = _convert_file(destination, output_dir)

    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
