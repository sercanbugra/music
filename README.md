# Simple Music Splitter

A minimal Spleeter project with:
- CLI script
- One-click BAT
- Flask web UI (upload MP3 -> split -> download stems)

## Folder layout

- `app.py` : Flask web app
- `src/music_splitter.py` : CLI script
- `templates/index.html` : web template
- `static/styles.css` : web styles
- `inputs/` : optional input folder for CLI/BAT
- `outputs/` : output folder for CLI/BAT
- `web_uploads/` : uploaded files from web UI
- `web_outputs/` : separated files from web UI

## Requirements

- Windows + PowerShell
- Python 3.10 or 3.11
- ffmpeg on PATH
- Spleeter installed in active venv

## Setup (example)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
```

If dependency resolution fails on your machine, install your known working versions first, then install `spleeter`.

## CLI usage

Single file:

```powershell
python src\music_splitter.py "inputs\song.mp3" --stems 4 --output outputs
```

All audio files in a folder:

```powershell
python src\music_splitter.py "inputs" --stems 4 --output outputs
```

## One-click BAT usage (Windows)

- Double-click `run_splitter.bat` to process all files inside `inputs/`.
- Or drag and drop a single audio file (or a folder) onto `run_splitter.bat`.
- If you have multiple Python installations, activate your Spleeter venv first, then run the BAT:
  `C:\Scripts\.venv2\Scripts\activate` then `C:\Scripts\Music\run_splitter.bat`.

## Web UI usage (Flask)

Start server:

```powershell
python app.py
```

Open browser:

`http://127.0.0.1:5000`

Flow:
- Upload an `.mp3` file
- Choose stems count (`4` default)
- Download generated `.wav` stems from the list

## Deploy (GitHub + Render)

This repo includes files needed for Render deployment:
- `requirements.txt`
- `.python-version`
- `render.yaml`

### 1. Push to GitHub

```powershell
cd C:\Scripts\Music
git init
git add .
git commit -m "Initial commit: Flask + Spleeter app"
git branch -M main
git remote add origin https://github.com/<your-user>/<your-repo>.git
git push -u origin main
```

### 2. Deploy on Render

- In Render dashboard: **New +** -> **Blueprint**
- Select your GitHub repo
- Render reads `render.yaml` automatically
- After deploy, open the generated `onrender.com` URL

### 3. Connect custom domain

- In Render service: **Settings** -> **Custom Domains** -> **Add Custom Domain**
- Add your domain/subdomain (example: `split.yourdomain.com`)
- Create the DNS record Render asks for at your DNS provider
- Wait for DNS propagation, then verify in Render

Notes:
- Render filesystem is ephemeral. Uploaded/generated files are not permanent between restarts.
- If needed, configure a persistent disk (paid plans) or external object storage.
