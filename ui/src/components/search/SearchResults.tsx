import type { SearchCandidate } from "../../types";
import { MusicNoteIcon, YoutubeIcon, HeartIcon, HeartFilledIcon } from "../shared/Icons";

interface Props {
  pageQuery: string;
  pageResults: SearchCandidate[];
  isSearching: boolean;
  searchError: string | null;
  playingTrackId: string | null;
  likedTrackIds?: Set<string>;
  onPlayTrack: (c: SearchCandidate) => void;
  onAnalyze: (c: SearchCandidate) => void;
  onToggleLike?: (c: SearchCandidate) => void;
}

export default function SearchResults({
  pageQuery,
  pageResults,
  isSearching,
  searchError,
  playingTrackId,
  likedTrackIds = new Set(),
  onPlayTrack,
  onAnalyze,
  onToggleLike,
}: Props) {
  return (
    <div className="fade-in">
      <div className="search-page-header">
        <span className="search-page-label">
          <YoutubeIcon />
          Results for "<strong>{pageQuery}</strong>"
        </span>
        {isSearching && (
          <span className="search-page-hint">
            <span className="search-page-dot-anim">Loading</span>
          </span>
        )}
        {searchError && <span className="nm-error">{searchError}</span>}
      </div>

      <div className="search-page-list">
        {pageResults.map((c, i) => (
          <div
            key={c.id}
            className={`search-page-item fade-in ${playingTrackId === c.id ? "active" : ""}`}
            onClick={() => onPlayTrack(c)}
          >
            <span className="search-page-num">
              {playingTrackId === c.id ? "▶" : i + 1}
            </span>
            {c.thumbnail ? (
              <img className="search-page-thumb" src={c.thumbnail} alt="" />
            ) : (
              <div className="search-page-thumb search-page-thumb--placeholder">
                <MusicNoteIcon />
              </div>
            )}
            <div className="search-page-meta">
              <div className="search-page-title">{c.title}</div>
              <div className="search-page-sub">
                {c.uploader} · {c.duration}
              </div>
            </div>
            <div className="search-page-actions-group">
              <button
                className="search-page-action like-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleLike?.(c);
                }}
                title="Лайкнуть"
              >
                {likedTrackIds.has(c.id) ? <HeartFilledIcon /> : <HeartIcon />}
              </button>
              <button
                className="search-page-action"
                onClick={(e) => {
                  e.stopPropagation();
                  onAnalyze(c);
                }}
              >
                Analyze →
              </button>
            </div>
          </div>
        ))}

        {/* Skeleton rows while loading more */}
        {isSearching &&
          pageResults.length < 20 &&
          Array.from({ length: Math.max(0, 20 - pageResults.length) }).map(
            (_, i) => (
              <div
                key={`sk-${i}`}
                className="search-page-item search-page-skeleton fade-in"
              >
                <span className="search-page-num">·</span>
                <div className="skeleton-thumb"></div>
                <div className="skeleton-meta">
                  <div className="skeleton-line skeleton-line--title"></div>
                  <div className="skeleton-line skeleton-line--sub"></div>
                </div>
              </div>
            )
          )}
      </div>
    </div>
  );
}
