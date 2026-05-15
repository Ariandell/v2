"""
Listening history endpoints — sync and retrieve recently played tracks.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..models import RecentlyPlayed
from ..schemas import TrackSync
from ..dependencies import get_db, get_or_create_user, ensure_liked_playlist

router = APIRouter(tags=["history"])


@router.post("/sync-history")
async def sync_history(track: TrackSync, db: Session = Depends(get_db)):
    """Record a track play in the user's listening history."""
    user = get_or_create_user(
        db, email=track.user_email, name=track.user_name, picture=track.user_picture,
    )
    ensure_liked_playlist(db, user)

    # Remove previous entry for this track (move to top of history)
    existing = (
        db.query(RecentlyPlayed)
        .filter(RecentlyPlayed.user_id == user.id, RecentlyPlayed.track_id == track.id)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()

    # Add new entry
    db.add(RecentlyPlayed(
        user_id=user.id,
        track_id=track.id,
        title=track.title,
        uploader=track.uploader,
        thumbnail=track.thumbnail,
        url=track.url,
        duration=track.duration,
    ))
    db.commit()
    return {"status": "synced"}


@router.get("/recent-tracks")
async def get_recent_tracks(email: str, db: Session = Depends(get_db)):
    """Get the 20 most recently played tracks for a user."""
    user = get_or_create_user(db, email=email)

    tracks = user.recent_tracks[:20]
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
            for t in tracks
        ]
    }
