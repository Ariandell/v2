import { useRef, useEffect, useState } from "react";
import type { SearchCandidate, Playlist } from "../../types";
import { streamUrl } from "../../api";
import { HeartIcon, HeartFilledIcon, SparklesIcon, ListIcon } from "../shared/Icons";

interface Props {
  track: SearchCandidate;
  playlist: SearchCandidate[];
  playlists?: Playlist[];
  likedTrackIds?: Set<string>;
  onTrackChange: (c: SearchCandidate) => void;
  onAnalyze?: () => void;
  onToggleLike?: (c: SearchCandidate) => void;
  onAddToPlaylist?: (playlistId: number, track: SearchCandidate) => void;
}

export default function Player({ 
  track, 
  playlist, 
  playlists = [],
  likedTrackIds = new Set(),
  onTrackChange, 
  onAnalyze,
  onToggleLike,
  onAddToPlaylist
}: Props) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isBuffering, setIsBuffering] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(0.2);
  const [showPlaylistPicker, setShowPlaylistPicker] = useState(false);
  const pickerRef = useRef<HTMLDivElement | null>(null);
  const retryCountRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const parsedDuration = (() => {
    if (!track.duration) return 0;
    const p = track.duration.split(':').map(Number);
    if (p.length === 2) return p[0] * 60 + p[1];
    if (p.length === 3) return p[0] * 3600 + p[1] * 60 + p[2];
    return 0;
  })();

  // ── Load & play when track changes ──────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    retryCountRef.current = 0;
    setCurrentTime(0);
    setIsBuffering(true);

    if (audioRef.current) {
      audioRef.current.volume = volume;
      audioRef.current.src = streamUrl(track.id);
      audioRef.current.load();
    }

    return () => {
      cancelled = true;
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    };
  }, [track.id]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume;
    }
  }, [volume]);

  // Close playlist picker on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setShowPlaylistPicker(false);
      }
    };
    if (showPlaylistPicker) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showPlaylistPicker]);

  // ── Auto-play when audio becomes ready ──────────────────────────────────
  const handleCanPlay = () => {
    setIsBuffering(false);
    retryCountRef.current = 0;
    audioRef.current?.play().catch(() => {});
  };

  // ── Retry on error (backend may still be downloading) ──────────────────
  const handleError = () => {
    const audio = audioRef.current;
    if (!audio) return;

    const MAX_RETRIES = 5;
    if (retryCountRef.current < MAX_RETRIES) {
      retryCountRef.current++;
      const delay = Math.min(1000 * retryCountRef.current, 4000);
      console.log(`[Player] Retry ${retryCountRef.current}/${MAX_RETRIES} in ${delay}ms...`);
      setIsBuffering(true);

      retryTimerRef.current = setTimeout(() => {
        if (audio) {
          // Append cache-bust param to force a new request
          audio.src = streamUrl(track.id) + `?r=${retryCountRef.current}`;
          audio.load();
        }
      }, delay);
    } else {
      console.error("[Player] Max retries reached");
      setIsBuffering(false);
    }
  };

  const togglePlayPause = () => {
    if (!audioRef.current) return;
    if (isPlaying) audioRef.current.pause();
    else audioRef.current.play().catch(() => {});
  };

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    if (audioRef.current && parsedDuration) {
      audioRef.current.currentTime = pos * parsedDuration;
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleVolumeClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    let pos = (e.clientX - rect.left) / rect.width;
    pos = Math.max(0, Math.min(1, pos));
    setVolume(pos);
  };

  const playPrevNext = (dir: number) => {
    const idx = playlist.findIndex((c) => c.id === track.id);
    const next = idx + dir;
    if (next >= 0 && next < playlist.length) onTrackChange(playlist[next]);
  };

  const fmt = (s: number) =>
    `${Math.floor(s / 60)}:${Math.floor(s % 60).toString().padStart(2, "0")}`;

  // Filter playlists: exclude Liked (that's handled by the heart button)
  const userPlaylists = playlists.filter(p => !p.is_liked_playlist);

  return (
    <div className="bottom-player fade-in">
      <audio
        ref={audioRef}
        crossOrigin="anonymous"
        preload="auto"
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onTimeUpdate={() => {
          if (audioRef.current) setCurrentTime(audioRef.current.currentTime);
        }}
        onCanPlay={handleCanPlay}
        onWaiting={() => setIsBuffering(true)}
        onEnded={() => {
          setIsPlaying(false);
          playPrevNext(1);
        }}
        onError={handleError}
      />

      {/* LEFT: Track Info */}
      <div className="player-left">
        <img className="player-thumb" src={track.thumbnail} alt="" />
        <div className="player-meta">
          <div className="player-title">{track.title}</div>
          <div className="player-artist">{track.uploader}</div>
        </div>
      </div>

      {/* CENTER: Playback Controls & Progress Bar */}
      <div className="player-center">
        <div className="player-controls">
          <button
            className="player-btn player-btn--small"
            onClick={() => playPrevNext(-1)}
            title="Previous"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>
          </button>
          <button
            className="player-btn player-btn--circle"
            onClick={togglePlayPause}
            title={isBuffering ? "Loading..." : isPlaying ? "Pause" : "Play"}
          >
            {isBuffering ? (
              <span className="player-spinner" />
            ) : isPlaying ? (
               <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
            ) : (
               <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M8 5v14l11-7z"/></svg>
            )}
          </button>
          <button
            className="player-btn player-btn--small"
            onClick={() => playPrevNext(1)}
            title="Next"
          >
             <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/></svg>
          </button>
        </div>
        <div className="player-playback-bar">
          <div className="player-time">{fmt(currentTime)}</div>
          <div className="player-progress-container" onClick={handleProgressClick}>
            <div
              className="player-progress-bar"
              style={{ width: `${parsedDuration ? (currentTime / parsedDuration) * 100 : 0}%` }}
            ></div>
          </div>
          <div className="player-time">{track.duration || "0:00"}</div>
        </div>
      </div>

      {/* RIGHT: Volume + Actions */}
      <div className="player-right">
        <div className="player-volume">
          <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20" style={{color: 'var(--text2)'}}>
            {volume === 0 ? (
              <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z" />
            ) : volume < 0.5 ? (
              <path d="M5 9v6h4l5 5V4L9 9H5zm11.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z" />
            ) : (
              <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
            )}
          </svg>
          <div className="volume-bar-container" onClick={handleVolumeClick}>
            <div className="volume-bar">
              <div className="volume-bar-fill" style={{ width: `${volume * 100}%` }}></div>
            </div>
          </div>
        </div>

        <div className="player-actions">
          <button 
            className="player-action-btn like-btn"
            onClick={() => onToggleLike?.(track)}
            title="Like"
          >
            {likedTrackIds.has(track.id) ? <HeartFilledIcon /> : <HeartIcon />}
          </button>

          <div className="player-playlist-picker" ref={pickerRef}>
            <button 
              className="player-action-btn"
              onClick={() => setShowPlaylistPicker(!showPlaylistPicker)}
              title="Add to playlist"
            >
              <ListIcon />
            </button>
            {showPlaylistPicker && (
              <div className="playlist-picker-dropdown">
                <div className="playlist-picker-header">Add to playlist</div>
                {userPlaylists.length === 0 ? (
                  <div className="playlist-picker-empty">No playlists yet. Create one in the sidebar!</div>
                ) : (
                  userPlaylists.map(pl => (
                    <button 
                      key={pl.id} 
                      className="playlist-picker-item"
                      onClick={() => {
                        onAddToPlaylist?.(pl.id, track);
                        setShowPlaylistPicker(false);
                      }}
                    >
                      {pl.name}
                      <span className="playlist-picker-count">{pl.track_count} tracks</span>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>

          <button 
            className="player-action-btn analyze-btn" 
            onClick={onAnalyze}
            title="Analyze vibe"
          >
            <SparklesIcon />
          </button>
        </div>
      </div>
    </div>
  );
}
