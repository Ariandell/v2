import type { AnalysisResult } from "../../types";
import { MusicNoteIcon, ArrowLeftIcon } from "../shared/Icons";

interface Props {
  result: AnalysisResult;
  showBackButton: boolean;
  onBack: () => void;
  onNewSearch: () => void;
}

export default function AnalysisView({
  result,
  showBackButton,
  onBack,
  onNewSearch,
}: Props) {
  return (
    <div className="fade-in">
      {/* Back button (if came from search page) */}
      {showBackButton && (
        <button className="back-btn" onClick={onBack}>
          <ArrowLeftIcon /> Back to results
        </button>
      )}

      {/* Track info bar */}
      <div className="nm-card">
        <div className="nm-track-row">
          <div className="nm-track-info">
            <div className="nm-track-disc"><MusicNoteIcon /></div>
            <div>
              <div className="nm-track-name">{result.filename}</div>
              <div className="nm-track-meta">AI analyzed</div>
            </div>
          </div>
          <button className="nm-btn" onClick={onNewSearch}>
            New search
          </button>
        </div>
      </div>

      {/* Genres + Emotions */}
      <div className="nm-grid">
        <div className="nm-card">
          <div className="nm-section-label">Top predicted genres</div>
          {result.predictions.map((pred, i) => (
            <div className="nm-genre-row" key={i}>
              <div className="nm-genre-top">
                <span className="nm-genre-name">{pred.genre}</span>
                <span className="nm-genre-pct">
                  {(pred.probability * 100).toFixed(1)}%
                </span>
              </div>
              <div className="nm-bar-track">
                <div
                  className="nm-bar-fill"
                  style={{ width: `${pred.probability * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>

        <div className="nm-card">
          <div className="nm-section-label">Emotional profile</div>
          {result.vibes.vibe_1 ? (
            <div className="nm-vibe-wrap">
              <div className="nm-vibe nm-vibe-accent">
                <div className="nm-vibe-role">Primary vibe</div>
                <div className="nm-vibe-name">{result.vibes.vibe_1}</div>
                <div className="nm-vibe-pct">
                  {((result.vibes.score_1 || 0) * 100).toFixed(0)}% match
                </div>
              </div>
              {result.vibes.vibe_2 && (
                <div className="nm-vibe">
                  <div className="nm-vibe-role">Secondary vibe</div>
                  <div className="nm-vibe-name" style={{ color: "var(--text2)" }}>
                    {result.vibes.vibe_2}
                  </div>
                  <div className="nm-vibe-pct" style={{ color: "var(--text3)" }}>
                    {((result.vibes.score_2 || 0) * 100).toFixed(0)}% match
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="nm-no-vibes">
              No vocals detected to establish vibe.
            </div>
          )}
        </div>
      </div>

      {/* Language & Lyrics */}
      <div className="nm-card">
        <div className="nm-section-label">Language &amp; lyrics</div>
        {result.is_instrumental ? (
          <div className="nm-instrumental-badge">Instrumental</div>
        ) : (
          <div className="nm-lang-badge">
            <div className="nm-lang-dot"></div>
            <span className="nm-lang-text">{result.language}</span>
          </div>
        )}
        {result.is_instrumental ? (
          <div className="nm-no-lyrics">
            No vocals detected — pure instrumental track.
          </div>
        ) : result.lyrics_english ? (
          <div className="nm-lyrics">"{result.lyrics_english}"</div>
        ) : (
          <div className="nm-no-lyrics">No translatable lyrics found.</div>
        )}
      </div>
    </div>
  );
}
