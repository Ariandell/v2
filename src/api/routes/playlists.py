"""
Playlist CRUD endpoints — create, list, add/remove tracks.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..models import Playlist, PlaylistTrack
from ..schemas import PlaylistCreate, TrackAdd
from ..dependencies import get_db, get_or_create_user, ensure_liked_playlist

router = APIRouter(prefix="/playlists", tags=["playlists"])


@router.get("")
async def get_playlists(email: str, db: Session = Depends(get_db)):
    """List all playlists for a user (auto-creates Liked playlist)."""
    user = get_or_create_user(db, email=email)
    ensure_liked_playlist(db, user)

    # Refresh to pick up any newly created playlist
    db.refresh(user)

    return {
        "playlists": [
            {
                "id": p.id,
                "name": p.name,
                "is_liked_playlist": p.is_liked_playlist,
                "created_at": str(p.created_at),
                "track_count": len(p.tracks),
            }
            for p in user.playlists
        ]
    }


@router.post("")
async def create_playlist(data: PlaylistCreate, db: Session = Depends(get_db)):
    """Create a new named playlist."""
    user = get_or_create_user(db, email=data.user_email)

    new_pl = Playlist(user_id=user.id, name=data.name)
    db.add(new_pl)
    db.commit()
    db.refresh(new_pl)
    return {"id": new_pl.id, "name": new_pl.name}


@router.post("/{playlist_id}/tracks")
async def add_track(playlist_id: int, track: TrackAdd, db: Session = Depends(get_db)):
    """Add a track to a playlist (idempotent — no duplicates)."""
    user = get_or_create_user(db, email=track.user_email)

    pl = (
        db.query(Playlist)
        .filter(Playlist.id == playlist_id, Playlist.user_id == user.id)
        .first()
    )
    if not pl:
        return JSONResponse(status_code=404, content={"error": "Playlist not found"})

    # Check if already in playlist
    existing = (
        db.query(PlaylistTrack)
        .filter(PlaylistTrack.playlist_id == playlist_id, PlaylistTrack.track_id == track.id)
        .first()
    )
    if existing:
        return {"status": "already_exists"}

    db.add(PlaylistTrack(
        playlist_id=playlist_id,
        track_id=track.id,
        title=track.title,
        uploader=track.uploader,
        thumbnail=track.thumbnail,
        url=track.url,
        duration=track.duration,
    ))
    db.commit()
    return {"status": "added"}


@router.get("/{playlist_id}/tracks")
async def get_tracks(playlist_id: int, email: str, db: Session = Depends(get_db)):
    """Get all tracks in a playlist."""
    user = get_or_create_user(db, email=email)

    pl = (
        db.query(Playlist)
        .filter(Playlist.id == playlist_id, Playlist.user_id == user.id)
        .first()
    )
    if not pl:
        return JSONResponse(status_code=404, content={"error": "Playlist not found"})

    return {
        "results": [
            {
                "id": t.track_id,
                "url": t.url,
                "title": t.title,
                "uploader": t.uploader,
                "thumbnail": t.thumbnail,
                "duration": t.duration,
            }
            for t in pl.tracks
        ]
    }


@router.delete("/{playlist_id}/tracks/{track_id}")
async def remove_track(playlist_id: int, track_id: str, email: str, db: Session = Depends(get_db)):
    """Remove a track from a playlist."""
    user = get_or_create_user(db, email=email)

    pl = (
        db.query(Playlist)
        .filter(Playlist.id == playlist_id, Playlist.user_id == user.id)
        .first()
    )
    if not pl:
        return JSONResponse(status_code=404, content={"error": "Playlist not found"})

    track = (
        db.query(PlaylistTrack)
        .filter(PlaylistTrack.playlist_id == playlist_id, PlaylistTrack.track_id == track_id)
        .first()
    )
    if track:
        db.delete(track)
        db.commit()

    return {"status": "removed"}
