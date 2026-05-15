"""
YouTube service — search, download, and stream audio.

Provides two search backends:
  1. InnerTube API (fast, ~200-500ms)
  2. yt-dlp subprocess fallback (~3-8s)
Plus audio download/caching for the streaming endpoint.
"""

import os
import sys
import json
import shutil
import asyncio
import tempfile
import subprocess
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_DURATION_SECS = 600  # 10 minutes — skip anything longer
YTDLP_PRINT_FMT = "%(id)s|||%(title)s|||%(uploader)s|||%(duration)s|||%(thumbnail)s"

MIME_MAP = {
    ".webm": "audio/webm",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".wav": "audio/wav",
}

_audio_cache_dir: Path | None = None

# In-memory cache of resolved direct YouTube CDN URLs.
# Key: video_id, Value: (url, timestamp)
# URLs expire after ~5 hours (YouTube gives ~6h validity)
_url_cache: dict[str, tuple[str, float]] = {}
_URL_TTL = 5 * 3600  # 5 hours


def get_audio_cache_dir() -> Path:
    """Return (and lazily create) the shared audio cache directory."""
    global _audio_cache_dir
    if _audio_cache_dir is None:
        _audio_cache_dir = Path(tempfile.gettempdir()) / "luna_audio_cache"
        _audio_cache_dir.mkdir(exist_ok=True)
    return _audio_cache_dir


# ── yt-dlp resolution ────────────────────────────────────────────────────────

def resolve_ytdlp() -> str:
    """Find the yt-dlp executable — PATH first, then .venv/Scripts."""
    found = shutil.which("yt-dlp")
    if found:
        return found
    venv_scripts = Path(sys.executable).parent
    for name in ("yt-dlp.exe", "yt-dlp"):
        candidate = venv_scripts / name
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError("yt-dlp not found in PATH or .venv/Scripts")


# ── InnerTube search (fast path) ─────────────────────────────────────────────

async def innertube_search(query: str, count: int) -> list[dict]:
    """Query YouTube InnerTube API directly via httpx — no subprocess."""
    import httpx

    payload = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20241001.00.00",
                "hl": "en",
                "gl": "US",
            }
        },
        "query": query,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://www.youtube.com/youtubei/v1/search?prettyPrint=false",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    candidates: list[dict] = []
    contents = (
        data.get("contents", {})
        .get("twoColumnSearchResultsRenderer", {})
        .get("primaryContents", {})
        .get("sectionListRenderer", {})
        .get("contents", [])
    )

    for section in contents:
        items = section.get("itemSectionRenderer", {}).get("contents", [])
        for item in items:
            vr = item.get("videoRenderer")
            if not vr:
                continue

            video_id = vr.get("videoId", "")
            title = "".join(
                r.get("text", "") for r in vr.get("title", {}).get("runs", [])
            )
            uploader = "".join(
                r.get("text", "") for r in vr.get("ownerText", {}).get("runs", [])
            )
            duration_text = vr.get("lengthText", {}).get("simpleText", "")

            if not _duration_ok(duration_text):
                continue

            thumbs = vr.get("thumbnail", {}).get("thumbnails", [])
            thumbnail = thumbs[-1]["url"] if thumbs else ""

            if video_id and title:
                candidates.append(_build_candidate(video_id, title, uploader, duration_text, thumbnail))

            if len(candidates) >= count:
                break
        if len(candidates) >= count:
            break

    return candidates


# ── yt-dlp search (fallback) ─────────────────────────────────────────────────

async def ytdlp_search(query: str, count: int) -> list[dict]:
    """Search YouTube via yt-dlp subprocess. Slower but more reliable."""
    fetch_count = count * 2  # over-fetch to account for duration filtering
    cmd = [
        resolve_ytdlp(),
        "--default-search", f"ytsearch{fetch_count}",
        "--flat-playlist",
        "--print", YTDLP_PRINT_FMT,
        "--no-warnings",
        query,
    ]

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = await asyncio.to_thread(
        lambda: subprocess.run(cmd, capture_output=True, timeout=30, env=env)
    )

    stdout = _decode_stdout(result.stdout)
    candidates: list[dict] = []

    for line in stdout.strip().split("\n"):
        parsed = parse_ytdlp_line(line)
        if parsed:
            candidates.append(parsed)
        if len(candidates) >= count:
            break

    return candidates


# ── Audio download / cache ───────────────────────────────────────────────────

async def download_or_cache(video_id: str) -> Path | None:
    """Download audio for a video ID (or return cached path). None on failure."""
    cache_dir = get_audio_cache_dir()

    # Check cache first (skip .tmp files)
    cached = [f for f in cache_dir.glob(f"{video_id}.*") if f.suffix != ".tmp"]
    if cached:
        print(f"[stream] Cache hit: {cached[0]}")
        return cached[0]

    # Download with optimized flags for speed
    output_template = str(cache_dir / f"{video_id}.%(ext)s")
    cmd = [
        resolve_ytdlp(),
        "-f", "bestaudio",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "--concurrent-fragments", "4",                        # parallel chunk download
        "--no-check-certificates",                            # skip TLS verify (local use)
        "-o", output_template,
        f"https://www.youtube.com/watch?v={video_id}",
    ]

    print(f"[stream] Downloading: {video_id}")
    result = await asyncio.to_thread(
        lambda: subprocess.run(cmd, capture_output=True, timeout=60)
    )

    if result.returncode != 0:
        err = result.stderr.decode(errors="replace").strip()
        out = result.stdout.decode(errors="replace").strip()
        print(f"[stream] yt-dlp FAILED (rc={result.returncode}): {err} | {out}")
        return None

    cached = [f for f in cache_dir.glob(f"{video_id}.*") if f.suffix != ".tmp"]
    if not cached:
        return None

    print(f"[stream] Serving: {cached[0]} ({cached[0].stat().st_size} bytes)")
    return cached[0]


def is_cached(video_id: str) -> Path | None:
    """Check if audio is already cached. Returns path or None."""
    cache_dir = get_audio_cache_dir()
    cached = [f for f in cache_dir.glob(f"{video_id}.*") if f.suffix != ".tmp"]
    return cached[0] if cached else None


async def get_direct_url(video_id: str) -> str | None:
    """
    Extract the direct audio URL from YouTube CDN (~1-2 seconds).
    Returns None on failure. Does NOT download the file.
    """
    cmd = [
        resolve_ytdlp(),
        "-f", "bestaudio",
        "--get-url",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "--no-check-certificates",
        f"https://www.youtube.com/watch?v={video_id}",
    ]

    try:
        result = await asyncio.to_thread(
            lambda: subprocess.run(cmd, capture_output=True, timeout=15)
        )
        if result.returncode == 0:
            url = result.stdout.decode("utf-8").strip()
            if url.startswith("http"):
                print(f"[stream] Got direct URL for {video_id}")
                return url
    except Exception as e:
        print(f"[stream] get_direct_url failed: {e}")

    return None


async def proxy_stream(direct_url: str):
    """
    Proxy-stream audio from YouTube CDN through our server.
    Yields chunks as they arrive — browser starts playing in ~1 second.
    Proper CORS headers are added by our middleware.
    """
    import httpx

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        async with client.stream("GET", direct_url) as resp:
            async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                yield chunk


async def stream_download(video_id: str):
    """
    Stream audio directly from yt-dlp stdout → client.
    Saves to cache file simultaneously so future requests are instant.

    Yields (chunk: bytes) as yt-dlp produces them.
    Playback starts within 1-2 seconds instead of waiting 10-15s for full download.
    """
    cache_dir = get_audio_cache_dir()
    temp_path = cache_dir / f"{video_id}.tmp"
    final_path = cache_dir / f"{video_id}.webm"

    cmd = [
        resolve_ytdlp(),
        "-f", "bestaudio",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "-o", "-",  # output to stdout
        f"https://www.youtube.com/watch?v={video_id}",
    ]

    print(f"[stream] Streaming download: {video_id}")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )

    try:
        with open(temp_path, "wb") as cache_file:
            while True:
                chunk = await proc.stdout.read(64 * 1024)  # 64KB chunks
                if not chunk:
                    break
                cache_file.write(chunk)
                yield chunk

        await proc.wait()

        # Rename temp → final on success
        if proc.returncode == 0 and temp_path.exists() and temp_path.stat().st_size > 0:
            temp_path.rename(final_path)
            print(f"[stream] Cached: {final_path} ({final_path.stat().st_size} bytes)")
        else:
            temp_path.unlink(missing_ok=True)

    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def get_mime_type(filepath: Path) -> str:
    """Return MIME type for an audio file based on extension."""
    return MIME_MAP.get(filepath.suffix.lower(), "audio/mpeg")


# ── Shared helpers ────────────────────────────────────────────────────────────

def parse_ytdlp_line(line: str) -> dict | None:
    """Parse one '|||'-delimited yt-dlp output line into a candidate dict."""
    if "|||" not in line:
        return None
    parts = line.split("|||")
    if len(parts) < 4:
        return None

    video_id = parts[0].strip()
    if not video_id:
        return None

    duration_raw = parts[3].strip() if len(parts) > 3 else ""
    thumbnail = parts[4].strip() if len(parts) > 4 else ""

    try:
        secs = int(float(duration_raw))
        if secs > MAX_DURATION_SECS:
            return None
        duration_fmt = f"{secs // 60}:{secs % 60:02d}"
    except (ValueError, TypeError):
        duration_fmt = duration_raw

    return _build_candidate(video_id, parts[1].strip(), parts[2].strip(), duration_fmt, thumbnail)


def _duration_ok(duration_text: str) -> bool:
    """Return True if a human-readable duration (e.g. '3:45') is ≤ 10 min."""
    if not duration_text:
        return True  # unknown length — allow
    parts = duration_text.split(":")
    if len(parts) == 3:
        return False  # hour-long
    if len(parts) == 2:
        try:
            return int(parts[0]) * 60 + int(parts[1]) <= MAX_DURATION_SECS
        except ValueError:
            return True
    return True


def _build_candidate(
    video_id: str, title: str, uploader: str, duration: str, thumbnail: str,
) -> dict:
    return {
        "id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": title,
        "uploader": uploader,
        "duration": duration,
        "thumbnail": thumbnail,
    }


def _decode_stdout(raw: bytes) -> str:
    """Try UTF-8 → CP1251 → CP866 fallback chain for Windows subprocess output."""
    for enc in ("utf-8", "cp1251"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("cp866", errors="replace")
