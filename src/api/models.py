from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    picture = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    recent_tracks = relationship("RecentlyPlayed", back_populates="user", order_by="RecentlyPlayed.played_at.desc()")
    playlists = relationship("Playlist", back_populates="user", order_by="Playlist.created_at.asc()")
    genres = relationship("UserGenre", back_populates="user", order_by="UserGenre.score.desc()")

class UserGenre(Base):
    __tablename__ = "user_genres"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    genre = Column(String)
    score = Column(Float) # Stores percentage/score like 80.0, 11.0, 9.0

    user = relationship("User", back_populates="genres")

class RecentlyPlayed(Base):
    __tablename__ = "recently_played"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    track_id = Column(String)  # YouTube ID
    title = Column(String)
    uploader = Column(String)
    thumbnail = Column(String)
    url = Column(String)
    duration = Column(String)
    played_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="recent_tracks")

class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    is_liked_playlist = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="playlists")
    tracks = relationship("PlaylistTrack", back_populates="playlist", order_by="PlaylistTrack.added_at.desc()")

class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"

    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id"))
    track_id = Column(String)
    title = Column(String)
    uploader = Column(String)
    thumbnail = Column(String)
    url = Column(String)
    duration = Column(String)
    added_at = Column(DateTime, default=datetime.utcnow)

    playlist = relationship("Playlist", back_populates="tracks")
