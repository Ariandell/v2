/**
 * HomeView — landing page with recently played tracks and playlists grid.
 */

import type { SearchCandidate, Playlist } from "../../types";
import { MusicNoteIcon, HeartFilledIcon, ListIcon } from "../shared/Icons";

interface Props {
  recentTracks: SearchCandidate[];
  playlists: Playlist[];
  onPlayTrack: (track: SearchCandidate) => void;
  onSelectPlaylist: (pl: Playlist) => void;
}

export default function HomeView({ recentTracks, playlists, onPlayTrack, onSelectPlaylist }: Props) {
  const visiblePlaylists = playlists
    .filter((pl) => !pl.is_liked_playlist || pl.track_count > 0)
    .sort((a, b) => (b.is_liked_playlist ? 1 : 0) - (a.is_liked_playlist ? 1 : 0));

  const isEmpty = recentTracks.length === 0 && playlists.length === 0;

  return (
    <div className="nm-idle-view fade-in">
      {/* Recently Played */}
      {recentTracks.length > 0 && (
        <>
          <h2 className="recent-tracks-title">Recently Played</h2>
          <div className="recent-tracks-grid">
            {recentTracks.map((c) => (
              <div key={c.id} className="recent-track-card" onClick={() => onPlayTrack(c)}>
                {c.thumbnail ? (
                  <img src={c.thumbnail} alt="" className="recent-track-thumb" />
                ) : (
                  <div className="recent-track-thumb recent-track-thumb--placeholder">
                    <MusicNoteIcon />
                  </div>
                )}
                <div className="recent-track-meta">
                  <div className="recent-track-title">{c.title}</div>
                  <div className="recent-track-sub">{c.uploader}</div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Playlists Grid */}
      {visiblePlaylists.length > 0 && (
        <>
          <h2 className="recent-tracks-title" style={{ marginTop: "40px" }}>
            Your Playlists
          </h2>
          <div className="recent-tracks-grid">
            {visiblePlaylists.map((pl) => (
              <div key={pl.id} className="recent-track-card" onClick={() => onSelectPlaylist(pl)}>
                <div className="recent-track-thumb recent-track-thumb--placeholder">
                  {pl.is_liked_playlist ? <HeartFilledIcon /> : <ListIcon />}
                </div>
                <div className="recent-track-meta">
                  <div className="recent-track-title">{pl.name}</div>
                  <div className="recent-track-sub">{pl.track_count} tracks</div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Welcome Card (empty state) */}
      {isEmpty && (
        <div className="nm-card welcome-card">
          <div className="nm-icon-circle">
            <MusicNoteIcon />
          </div>
          <div className="nm-drop-title">Search a song to analyze</div>
          <div className="nm-drop-sub">
            Type a track name and press <kbd>Enter</kbd> to browse results,
            or select from the autocomplete dropdown.
            <br />
            Click <strong>Import</strong> to upload a local audio file.
          </div>
        </div>
      )}
    </div>
  );
}
