/**
 * usePlayer — audio player state + recently played tracks.
 * Manages which track is playing, recent tracks list, and history sync.
 */

import { useState, useCallback } from "react";
import type { SearchCandidate, UserInfo } from "../types";
import { syncHistory } from "../api";

export function usePlayer(user: UserInfo | null) {
  const [playingTrack, setPlayingTrack] = useState<SearchCandidate | null>(null);
  const [recentTracks, setRecentTracks] = useState<SearchCandidate[]>(() => {
    try {
      const saved = localStorage.getItem("recent_tracks");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const handlePlayTrack = useCallback(
    (track: SearchCandidate) => {
      setPlayingTrack(track);
      setRecentTracks((prev) => {
        const filtered = prev.filter((t) => t.id !== track.id);
        const next = [track, ...filtered].slice(0, 12);
        localStorage.setItem("recent_tracks", JSON.stringify(next));
        return next;
      });

      // Sync to database if user is logged in
      if (user) {
        syncHistory(track, user);
      }
    },
    [user],
  );

  return {
    playingTrack,
    recentTracks,
    setRecentTracks,
    handlePlayTrack,
  };
}
