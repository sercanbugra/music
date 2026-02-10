from __future__ import annotations

import shutil
import subprocess
import sys
import uuid
import os
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "web_uploads"
OUTPUT_DIR = BASE_DIR / "web_outputs"
ALLOWED_EXTENSIONS = {".mp3"}
DEFAULT_STEMS = 4

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "music-splitter-local-dev")
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024


def ensure_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def check_dependencies() -> tuple[bool, str]:
    if shutil.which("ffmpeg") is None:
        return False, "ffmpeg was not found. Add it to PATH."

    try:
        subprocess.run(
            [sys.executable, "-m", "spleeter", "--help"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return False, f"Spleeter is not installed in this Python environment: {sys.executable}"

    return True, ""


def run_separation(input_file: Path, stems: int) -> tuple[bool, str, str]:
    job_id = uuid.uuid4().hex[:8]
    job_output = OUTPUT_DIR / job_id
    job_output.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "spleeter",
        "separate",
        "-p",
        f"spleeter:{stems}stems",
        "-o",
        str(job_output),
        str(input_file),
    ]

    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.returncode != 0:
        return False, job_id, (completed.stderr or completed.stdout or "Unknown error").strip()

    track_folder = input_file.stem
    return True, job_id, track_folder


def list_stems(job_id: str, track_folder: str) -> list[str]:
    target = OUTPUT_DIR / job_id / track_folder
    if not target.exists():
        return []
    return sorted([f.name for f in target.iterdir() if f.is_file() and f.suffix.lower() == ".wav"])


@app.get("/")
def index():
    return render_template("index.html", stems=DEFAULT_STEMS, files=[], job_id="", track_folder="")


@app.post("/separate")
def separate():
    ensure_dirs()
    ok, dep_error = check_dependencies()
    if not ok:
        flash(dep_error, "error")
        return redirect(url_for("index"))

    upload = request.files.get("audio_file")
    if upload is None or upload.filename is None or upload.filename.strip() == "":
        flash("Please select an MP3 file.", "error")
        return redirect(url_for("index"))

    filename = secure_filename(upload.filename)
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        flash("Only .mp3 files are accepted.", "error")
        return redirect(url_for("index"))

    stems = request.form.get("stems", str(DEFAULT_STEMS))
    try:
        stems_value = int(stems)
    except ValueError:
        stems_value = DEFAULT_STEMS
    if stems_value not in {2, 4, 5}:
        stems_value = DEFAULT_STEMS

    job_prefix = uuid.uuid4().hex[:8]
    saved_name = f"{job_prefix}_{filename}"
    input_path = UPLOAD_DIR / saved_name
    upload.save(input_path)

    success, job_id, result = run_separation(input_path, stems_value)
    if not success:
        flash(f"Separation failed: {result}", "error")
        return redirect(url_for("index"))

    stem_files = list_stems(job_id, result)
    if not stem_files:
        flash("Output files were not found.", "error")
        return redirect(url_for("index"))

    flash("Separation completed. You can download the stems below.", "success")
    return render_template(
        "index.html",
        stems=stems_value,
        files=stem_files,
        job_id=job_id,
        track_folder=result,
    )


@app.get("/download/<job_id>/<track_folder>/<filename>")
def download(job_id: str, track_folder: str, filename: str):
    safe_job = secure_filename(job_id)
    safe_track = secure_filename(track_folder)
    safe_name = secure_filename(filename)
    target = OUTPUT_DIR / safe_job / safe_track / safe_name

    if not target.exists() or target.suffix.lower() != ".wav":
        flash("File not found.", "error")
        return redirect(url_for("index"))

    return send_file(target, as_attachment=True, download_name=target.name)


if __name__ == "__main__":
    ensure_dirs()
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
