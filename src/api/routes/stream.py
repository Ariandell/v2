"""
Audio streaming endpoint — fast YouTube CDN proxy + local cache.

Strategy:
  1. Cached  → FileResponse (instant, seekable)
  2. Not cached → get direct YouTube CDN URL (~1-2s) → proxy-stream it
     + start background download to cache for next time
"""

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse

from ..services import youtube as yt

router = APIRouter(tags=["stream"])


@router.get("/stream/{video_id}")
async def stream_audio(video_id: str, background_tasks: BackgroundTasks):
    """
    Serve YouTube audio. Two modes:
      - Cached: instant FileResponse with Range/seeking support
      - Not cached: proxy-stream from YouTube CDN (plays in ~1-2s)
        + background task downloads for future cache hits
    """
    # ── Fast path: already cached → instant seekable response ──
    cached_path = yt.is_cached(video_id)
    if cached_path:
        return FileResponse(
            path=str(cached_path),
            media_type=yt.get_mime_type(cached_path),
            filename=f"{video_id}{cached_path.suffix}",
        )

    # ── Slow path: proxy from YouTube CDN ──
    try:
        yt.resolve_ytdlp()  # fail fast if yt-dlp missing
    except FileNotFoundError:
        return JSONResponse(status_code=500, content={"error": "yt-dlp not found"})

    # Get direct URL from YouTube (~1-2s)
    direct_url = await yt.get_direct_url(video_id)
    if not direct_url:
        # Fallback: full download then serve
        filepath = await yt.download_or_cache(video_id)
        if filepath is None:
            return JSONResponse(status_code=500, content={"error": "Failed to get audio."})
        return FileResponse(
            path=str(filepath),
            media_type=yt.get_mime_type(filepath),
            filename=f"{video_id}{filepath.suffix}",
        )

    # Start caching in background for next time
    background_tasks.add_task(yt.download_or_cache, video_id)

    # Proxy-stream from YouTube CDN → browser (instant playback)
    return StreamingResponse(
        yt.proxy_stream(direct_url),
        media_type="audio/webm",
        headers={
            "Content-Disposition": f'inline; filename="{video_id}.webm"',
            "Cache-Control": "no-cache",
        },
    )


@router.post("/prefetch")
async def prefetch_tracks(payload: dict, background_tasks: BackgroundTasks):
    """
    Pre-download audio for a list of video IDs in the background.
    Called by frontend when search results appear.
    """
    ids = payload.get("ids", [])[:3]
    for video_id in ids:
        if not yt.is_cached(video_id):
            background_tasks.add_task(yt.download_or_cache, video_id)

    return {"status": "prefetching", "count": len(ids)}
