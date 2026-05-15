"""
YouTube search endpoints — fast InnerTube + yt-dlp fallback + SSE streaming.
"""

import json
import asyncio

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse

from ..services import youtube as yt

router = APIRouter(tags=["search"])


@router.get("/search")
async def search_youtube(q: str = Query(..., description="Search query"), count: int = Query(5)):
    """
    Search YouTube — InnerTube first (fast), yt-dlp fallback (reliable).
    Returns up to `count` results filtered to ≤ 10 min duration.
    """
    query = q.strip()
    if not query:
        return JSONResponse(status_code=400, content={"error": "Empty query"})

    # Fast path: InnerTube API (~200-500ms)
    try:
        candidates = await yt.innertube_search(query, count)
        if candidates:
            return {"query": q, "results": candidates}
    except Exception as e:
        print(f"[search] InnerTube failed, falling back to yt-dlp: {e}")

    # Fallback: yt-dlp subprocess (~3-8s)
    try:
        candidates = await yt.ytdlp_search(query, count)
        return {"query": q, "results": candidates}
    except TimeoutError:
        return JSONResponse(status_code=504, content={"error": "Search timed out."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/search_stream")
async def search_stream(q: str = Query(...), count: int = Query(20, ge=1, le=50)):
    """
    Stream search results as Server-Sent Events.
    Each result is emitted immediately as yt-dlp finds it.
    """
    query = q.strip()
    if not query:
        return JSONResponse(status_code=400, content={"error": "Empty query"})

    async def _generate():
        cmd = [
            yt.resolve_ytdlp(),
            "--default-search", f"ytsearch{count}",
            "--flat-playlist",
            "--print", yt.YTDLP_PRINT_FMT,
            "--no-warnings",
            query,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            async for raw_line in proc.stdout:
                line = raw_line.decode("utf-8", errors="replace").rstrip()
                candidate = yt.parse_ytdlp_line(line)
                if candidate:
                    yield f"data: {json.dumps(candidate, ensure_ascii=False)}\n\n"
            await proc.wait()
        except Exception as exc:
            yield f'data: {{"error": "{exc}"}}\n\n'
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
