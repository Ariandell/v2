/**
 * usePlaylists — playlist CRUD, likes, and track management.
 */

import { useState, useEffect } from "react";
import type { SearchCandidate, UserInfo, Playlist } from "../types";
import {
  fetchPlaylists,
  fetchPlaylistTracks,
  createPlaylist,
  addTrackToPlaylist,
  removeTrackFromPlaylist,
  fetchRecentTracks,
} from "../api";

interface UsePlaylistsOptions {
  user: UserInfo | null;
  setRecentTracks: (tracks: SearchCandidate[]) => void;
}

export function usePlaylists({ user, setRecentTracks }: UsePlaylistsOptions) {
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [likedTrackIds, setLikedTrackIds] = useState<Set<string>>(new Set());
  const [playlistTracks, setPlaylistTracks] = useState<Record<number, SearchCandidate[]>>({});

  // Load playlists and recent tracks when user logs in
  useEffect(() => {
    if (!user) {
      setPlaylists([]);
      setLikedTrackIds(new Set());
      setPlaylistTracks({});
      setRecentTracks([]);
      return;
    }

    fetchRecentTracks(user.email).then((tracks) => {
      if (tracks?.length > 0) setRecentTracks(tracks);
    });

    fetchPlaylists(user.email).then((pls) => {
      if (pls?.length > 0) setPlaylists(pls);
      const likedPl = pls.find((p) => p.is_liked_playlist);
      if (likedPl) {
        fetchPlaylistTracks(likedPl.id, user.email).then((tracks) => {
          setLikedTrackIds(new Set(tracks.map((t) => t.id)));
          setPlaylistTracks((prev) => ({ ...prev, [likedPl.id]: tracks }));
        });
      }
    });
  }, [user]);

  /** Update a single playlist's track_count in state */
  const updatePlaylistTrackCount = (plId: number, tracks: SearchCandidate[]) => {
    setPlaylists((prev) =>
      prev.map((p) => (p.id === plId ? { ...p, track_count: tracks.length } : p)),
    );
  };

  /** Toggle like on a track */
  const handleToggleLike = async (track: SearchCandidate) => {
    if (!user) {
      alert("Please log in to like tracks.");
      return;
    }
    const likedPl = playlists.find((p) => p.is_liked_playlist);
    if (!likedPl) return;

    const newLiked = new Set(likedTrackIds);
    const currentTracks = playlistTracks[likedPl.id] || [];

    try {
      if (newLiked.has(track.id)) {
        newLiked.delete(track.id);
        const updated = currentTracks.filter((t) => t.id !== track.id);
        setPlaylistTracks((prev) => ({ ...prev, [likedPl.id]: updated }));
        updatePlaylistTrackCount(likedPl.id, updated);
        await removeTrackFromPlaylist(likedPl.id, track.id, user.email);
      } else {
        newLiked.add(track.id);
        const updated = [track, ...currentTracks];
        setPlaylistTracks((prev) => ({ ...prev, [likedPl.id]: updated }));
        updatePlaylistTrackCount(likedPl.id, updated);
        await addTrackToPlaylist(likedPl.id, track, user.email);
      }
      setLikedTrackIds(newLiked);
      const pls = await fetchPlaylists(user.email);
      setPlaylists(pls);
    } catch (err: any) {
      console.error("Failed to toggle like:", err);
      alert("Failed to toggle like. Is the server running?");
    }
  };

  /** Add a track to any playlist */
  const handleAddToPlaylist = async (playlistId: number, track: SearchCandidate) => {
    if (!user) {
      alert("Please log in to add tracks to playlist.");
      return;
    }
    const currentTracks = playlistTracks[playlistId] || [];
    if (currentTracks.find((t) => t.id === track.id)) return;

    try {
      const updated = [track, ...currentTracks];
      setPlaylistTracks((prev) => ({ ...prev, [playlistId]: updated }));
      updatePlaylistTrackCount(playlistId, updated);
      await addTrackToPlaylist(playlistId, track, user.email);
      const pls = await fetchPlaylists(user.email);
      setPlaylists(pls);
    } catch (err: any) {
      console.error("Failed to add to playlist:", err);
      alert("Failed to add to playlist. Is the server running?");
    }
  };

  /** Create a new playlist */
  const handleCreatePlaylist = async (name: string) => {
    if (!user) {
      alert("Please log in to create a playlist.");
      return;
    }
    await createPlaylist(name, user.email);
    const pls = await fetchPlaylists(user.email);
    setPlaylists(pls);
  };

  /** Load tracks for a specific playlist */
  const loadPlaylistTracks = async (pl: Playlist): Promise<SearchCandidate[]> => {
    if (!user) return [];
    const tracks = await fetchPlaylistTracks(pl.id, user.email);
    setPlaylistTracks((prev) => ({ ...prev, [pl.id]: tracks }));
    return tracks;
  };

  return {
    playlists,
    likedTrackIds,
    handleToggleLike,
    handleAddToPlaylist,
    handleCreatePlaylist,
    loadPlaylistTracks,
  };
}
