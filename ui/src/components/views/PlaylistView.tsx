/**
 * PlaylistView — display tracks inside a selected playlist.
 */

import type { SearchCandidate, Playlist } from "../../types";
import { MusicNoteIcon, ListIcon } from "../shared/Icons";

interface Props {
  playlist: Playlist;
  tracks: SearchCandidate[];
  playingTrackId: string | null;
  onPlayTrack: (track: SearchCandidate) => void;
}

export default function PlaylistView({ playlist, tracks, playingTrackId, onPlayTrack }: Props) {
  return (
    <div className="nm-playlist-view fade-in">
      <div className="search-page-header">
        <span className="search-page-label">
          <ListIcon /> {playlist.name}
        </span>
        <span className="search-page-hint">{playlist.track_count} tracks</span>
      </div>

      <div className="search-page-list">
        {tracks.length > 0 ? (
          tracks.map((t, i) => (
            <div
              key={t.id}
              className={`search-page-item${playingTrackId === t.id ? " active" : ""}`}
            >
              <span className="search-page-num">{i + 1}</span>
              {t.thumbnail ? (
                <img src={t.thumbnail} alt="" className="search-page-thumb" />
              ) : (
                <div className="search-page-thumb search-page-thumb--placeholder">
                  <MusicNoteIcon />
                </div>
              )}
              <div
                className="search-page-meta"
                onClick={() => onPlayTrack(t)}
                style={{ cursor: "pointer" }}
              >
                <div className="search-page-title">{t.title}</div>
                <div className="search-page-artist">{t.uploader}</div>
              </div>
              <span className="search-page-dur">{t.duration}</span>
            </div>
          ))
        ) : (
          <div
            className="nm-empty-state"
            style={{ padding: "40px", textAlign: "center", opacity: 0.5 }}
          >
            This playlist is empty.
          </div>
        )}
      </div>
    </div>
  );
}
