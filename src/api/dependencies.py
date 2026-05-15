"""
Shared FastAPI dependencies for user management and DB access.
Eliminates duplicate user-lookup / liked-playlist logic across routes.
"""

from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import User, Playlist


def get_db():
    """Yield a SQLAlchemy session, auto-closed after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_user(
    db: Session,
    email: str,
    name: str = "User",
    picture: str = "",
) -> User:
    """Find user by email or create a new one. Returns the User row."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, name=name, picture=picture)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def ensure_liked_playlist(db: Session, user: User) -> Playlist:
    """Make sure the user has a 'Liked Tracks' playlist. Returns it."""
    liked = (
        db.query(Playlist)
        .filter(Playlist.user_id == user.id, Playlist.is_liked_playlist == True)
        .first()
    )
    if not liked:
        liked = Playlist(user_id=user.id, name="Liked Tracks", is_liked_playlist=True)
        db.add(liked)
        db.commit()
        db.refresh(liked)
    return liked
