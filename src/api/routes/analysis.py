"""
Analysis endpoints — upload or URL-based AI genre analysis.
"""

import os
import re
import subprocess
from pathlib import Path

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse

from ..services.ai_models import ModelRegistry
from ..services.audio_analysis import run_analysis
from ..services.youtube import resolve_ytdlp
from ..schemas import AnalyzeUrlRequest

router = APIRouter(tags=["analysis"])

# Will be set by app.py at startup
_registry: ModelRegistry | None = None


def init(registry: ModelRegistry) -> None:
    """Called once at app startup to inject the model registry."""
    global _registry
    _registry = registry


# ── POST /analyze — upload a file ─────────────────────────────────────────────

@router.post("/analyze")
async def analyze_song(file: UploadFile = File(...)):
    """Upload an audio file and run the full AI analysis pipeline."""
    if not file.filename.endswith((".mp3", ".wav", ".flac")):
        return JSONResponse(
            status_code=400,
            content={"error": "Unsupported file type. Use mp3, wav, or flac."},
        )

    temp_path = Path("temp_audio") / file.filename
    temp_path.parent.mkdir(exist_ok=True)

    with open(temp_path, "wb") as f:
        f.write(await file.read())

    print(f"\nProcessing request for: {file.filename}")

    try:
        result = run_analysis(temp_path, display_name=file.filename, registry=_registry)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        if temp_path.exists():
            os.remove(temp_path)


# ── POST /analyze_url — download from YouTube + analyze ───────────────────────

@router.post("/analyze_url")
async def analyze_url(payload: AnalyzeUrlRequest):
    """Download a YouTube track by URL and run the full AI analysis."""
    url = payload.url.strip()
    title = payload.title.strip()

    if not url:
        return JSONResponse(status_code=400, content={"error": "No URL provided."})

    # Sanitize filename
    safe_name = re.sub(r'[<>:"/\\|?*]', "", title)[:100] or "track"
    temp_dir = Path("temp_audio")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"{safe_name}.wav"

    print(f"\n[analyze_url] Downloading: {url}")

    cmd = [
        resolve_ytdlp(),
        "--extractor-args", "youtube:player_client=android",
        "-x",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "-o", str(temp_path),
        "--no-playlist",
        "--no-warnings",
        "--quiet",
        url,
    ]

    try:
        subprocess.run(cmd, capture_output=True, timeout=300)

        # yt-dlp on Windows may add .wav extension even if already present
        if not temp_path.exists():
            alt = temp_dir / f"{safe_name}.wav.wav"
            if alt.exists():
                alt.rename(temp_path)

        if not temp_path.exists() or temp_path.stat().st_size == 0:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to download audio from YouTube."},
            )

        print(f"[analyze_url] Download OK — running analysis for: {title}")
        result = run_analysis(temp_path, display_name=title, registry=_registry)
        return result

    except subprocess.TimeoutExpired:
        return JSONResponse(
            status_code=504,
            content={"error": "Download timed out. The video may be too long."},
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass
