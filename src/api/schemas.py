"""
Pydantic schemas for API request/response validation.
All API data contracts live here for easy discovery and reuse.
"""

from pydantic import BaseModel


# ── Track Schemas ─────────────────────────────────────────────────────────────

class TrackBase(BaseModel):
    """Shared fields for any track reference."""
    id: str
    url: str
    title: str
    uploader: str
    duration: str
    thumbnail: str


class TrackSync(TrackBase):
    """POST /sync-history — track + user info for history sync."""
    user_email: str
    user_name: str
    user_picture: str


class TrackAdd(TrackBase):
    """POST /playlists/{id}/tracks — track + user email."""
    user_email: str


# ── Playlist Schemas ──────────────────────────────────────────────────────────

class PlaylistCreate(BaseModel):
    """POST /playlists — create a new playlist."""
    name: str
    user_email: str


# ── Analysis Schemas ──────────────────────────────────────────────────────────

class AnalyzeUrlRequest(BaseModel):
    """POST /analyze_url — download and analyze a YouTube track."""
    url: str
    title: str = "track"
