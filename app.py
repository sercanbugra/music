from __future__ import annotations

import threading
import shutil
import subprocess
import sys
import uuid
import os
import json
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "web_uploads"
OUTPUT_DIR = BASE_DIR / "web_outputs"
JOB_DIR = BASE_DIR / "web_jobs"
ALLOWED_EXTENSIONS = {".mp3"}
DEFAULT_STEMS = int(os.getenv("DEFAULT_STEMS", "2"))
MAX_ALLOWED_STEMS = int(os.getenv("MAX_ALLOWED_STEMS", "4"))
JOB_STATUS_PROCESSING = "processing"
JOB_STATUS_DONE = "done"
JOB_STATUS_ERROR = "error"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "music-splitter-local-dev")
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH_MB", "40")) * 1024 * 1024
JOBS: dict[str, dict[str, object]] = {}
JOBS_LOCK = threading.Lock()


def ensure_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    JOB_DIR.mkdir(parents=True, exist_ok=True)


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
        raw_error = (completed.stderr or completed.stdout or "").strip()
        if raw_error and "ERROR" not in raw_error and "Traceback" not in raw_error:
            raw_error = (
                f"{raw_error} | Process exited with code {completed.returncode}. "
                "Likely memory limit or machine stop."
            )
        if not raw_error:
            raw_error = (
                f"Process exited with code {completed.returncode}. "
                "Likely memory limit or machine stop."
            )
        return False, job_id, raw_error

    track_folder = input_file.stem
    return True, job_id, track_folder


def set_job(job_id: str, data: dict[str, object]) -> None:
    with JOBS_LOCK:
        if job_id not in JOBS:
            JOBS[job_id] = {}
        JOBS[job_id].update(data)
        payload = JOBS[job_id]
    save_job(job_id, payload)


def get_job(job_id: str) -> dict[str, object] | None:
    with JOBS_LOCK:
        if job_id in JOBS:
            return JOBS[job_id]
    disk_job = load_job(job_id)
    if disk_job is None:
        return None
    with JOBS_LOCK:
        JOBS[job_id] = disk_job
    return disk_job


def job_file(job_id: str) -> Path:
    return JOB_DIR / f"{job_id}.json"


def save_job(job_id: str, data: dict[str, object]) -> None:
    path = job_file(job_id)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(data, stream)


def load_job(job_id: str) -> dict[str, object] | None:
    path = job_file(job_id)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def process_job(job_id: str, input_path: Path, stems_value: int) -> None:
    success, result_job_id, result = run_separation(input_path, stems_value)
    if not success:
        set_job(
            job_id,
            {
                "status": JOB_STATUS_ERROR,
                "error": f"Separation failed: {result}",
            },
        )
        return

    stem_files = list_stems(result_job_id, result)
    if not stem_files:
        set_job(
            job_id,
            {
                "status": JOB_STATUS_ERROR,
                "error": "Output files were not found.",
            },
        )
        return

    set_job(
        job_id,
        {
            "status": JOB_STATUS_DONE,
            "files": stem_files,
            "track_folder": result,
            "error": "",
        },
    )


def list_stems(job_id: str, track_folder: str) -> list[str]:
    target = OUTPUT_DIR / job_id / track_folder
    if not target.exists():
        return []
    return sorted([f.name for f in target.iterdir() if f.is_file() and f.suffix.lower() == ".wav"])


@app.get("/")
def index():
    return render_template(
        "index.html",
        stems=DEFAULT_STEMS,
        files=[],
        job_id="",
        track_folder="",
        job_status="",
        error_message="",
    )


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
    if stems_value not in {2, 4}:
        stems_value = DEFAULT_STEMS
    if stems_value > MAX_ALLOWED_STEMS:
        stems_value = MAX_ALLOWED_STEMS

    job_prefix = uuid.uuid4().hex[:8]
    saved_name = f"{job_prefix}_{filename}"
    input_path = UPLOAD_DIR / saved_name
    upload.save(input_path)

    job_id = uuid.uuid4().hex[:8]
    set_job(
        job_id,
        {
            "status": JOB_STATUS_PROCESSING,
            "files": [],
            "track_folder": "",
            "error": "",
            "stems": stems_value,
        },
    )

    worker = threading.Thread(
        target=process_job,
        args=(job_id, input_path, stems_value),
        daemon=True,
    )
    worker.start()
    return redirect(url_for("job_status", job_id=job_id))


@app.get("/job/<job_id>")
def job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        flash("Job was not found.", "error")
        return redirect(url_for("index"))

    status = str(job.get("status", ""))
    files = list(job.get("files", []))
    track_folder = str(job.get("track_folder", ""))
    error_message = str(job.get("error", ""))
    stems_value = int(job.get("stems", DEFAULT_STEMS))

    return render_template(
        "index.html",
        stems=stems_value,
        files=files,
        job_id=job_id,
        track_folder=track_folder,
        job_status=status,
        error_message=error_message,
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

