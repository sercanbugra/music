#!/usr/bin/env python
"""Simple wrapper around Spleeter CLI for file/folder batch separation."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Separate songs into stems using installed Spleeter."
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="Audio file path or folder path containing audio files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs"),
        help="Output folder for separated stems (default: outputs).",
    )
    parser.add_argument(
        "--stems",
        choices=(2, 4, 5),
        type=int,
        default=4,
        help="Number of stems (2, 4, or 5).",
    )
    return parser.parse_args()


def collect_audio_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]

    if path.is_dir():
        files = [f for f in path.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS]
        return sorted(files)

    return []


def check_dependencies() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is not available on PATH.")

    try:
        subprocess.run(
            [sys.executable, "-m", "spleeter", "--help"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Spleeter CLI is not available in this Python environment."
        ) from exc


def run_separation(audio_file: Path, output_dir: Path, stems: int) -> int:
    cmd = [
        sys.executable,
        "-m",
        "spleeter",
        "separate",
        "-p",
        f"spleeter:{stems}stems",
        "-o",
        str(output_dir),
        str(audio_file),
    ]

    print(f"[RUN] {audio_file.name}")
    completed = subprocess.run(cmd)
    return completed.returncode


def main() -> int:
    args = parse_args()
    check_dependencies()

    audio_files = collect_audio_files(args.input_path)
    if not audio_files:
        print("No supported audio files found.")
        return 1

    args.output.mkdir(parents=True, exist_ok=True)

    failures = 0
    for audio_file in audio_files:
        failures += int(run_separation(audio_file, args.output, args.stems) != 0)

    if failures:
        print(f"Done with {failures} failed file(s).")
        return 1

    print("Done. All files separated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
