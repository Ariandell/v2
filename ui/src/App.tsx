/**
 * App — root component (thin orchestrator).
 *
 * All state logic is delegated to custom hooks.
 * This component only wires hooks together and renders the layout.
 */

import { useState } from "react";
import "./App.css";

import type { SearchCandidate, AnalysisResult, Playlist } from "./types";
import { analyzeUrl, analyzeFile } from "./api";

// Hooks
import { useAuth } from "./hooks/useAuth";
import { useSearch } from "./hooks/useSearch";
import { usePlayer } from "./hooks/usePlayer";
import { usePlaylists } from "./hooks/usePlaylists";

// Components
import { ImportIcon, SparklesIcon } from "./components/shared";
import { SearchBar, SearchResults } from "./components/search";
import { AnalysisView, HomeView, PlaylistView } from "./components/views";
import { Player } from "./components/player";
import { ImportModal, CreatePlaylistModal } from "./components/modals";
import { Sidebar } from "./components/layout";

// ── App ──────────────────────────────────────────────────────────────────────

function App() {
  // ── Hooks ────────────────────────────────────────────────────────────────
  const auth = useAuth();
  const search = useSearch();
  const player = usePlayer(auth.user);
  const playlists = usePlaylists({
    user: auth.user,
    setRecentTracks: player.setRecentTracks,
  });

  // ── Local UI state ───────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<"home" | "search" | "analysis" | "playlist">("home");
  const [selectedPlaylist, setSelectedPlaylist] = useState<Playlist | null>(null);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showCreatePlaylistModal, setShowCreatePlaylistModal] = useState(false);

  // ── Analysis state ───────────────────────────────────────────────────────
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingLabel, setProcessingLabel] = useState("Analyzing track...");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<AnalysisResult[]>([]);

  // ── Handlers ─────────────────────────────────────────────────────────────

  const handleSearchSubmit = async () => {
    await search.handleSearchSubmit();
    setActiveTab("search");
  };

  const handleSelectCandidate = async (candidate: SearchCandidate) => {
    search.setShowDropdown(false);
    setError(null);
    setIsProcessing(true);
    setActiveTab("analysis");
    setProcessingLabel(`Downloading "${candidate.title}"...`);

    try {
      const data = await analyzeUrl(candidate.url, candidate.title);
      setResult(data);
      setHistory((prev) => [data, ...prev.slice(0, 19)]);
    } catch (err: any) {
      setError(err.message || "Failed to analyze track.");
    } finally {
      setIsProcessing(false);
      setProcessingLabel("Analyzing track...");
    }
  };

  const handleFileSelected = async (file: File) => {
    if (!file.name.endsWith(".mp3") && !file.name.endsWith(".wav") && !file.name.endsWith(".flac")) {
      setError("Please upload an MP3, WAV, or FLAC file.");
      return;
    }
    setShowImportModal(false);
    setError(null);
    setResult(null);
    setIsProcessing(true);
    setProcessingLabel("Analyzing track...");

    try {
      const data = await analyzeFile(file);
      setResult(data);
      setHistory((prev) => [data, ...prev.slice(0, 19)]);
    } catch (err: any) {
      setError(err.message || "Failed to analyze the song.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSelectPlaylist = async (pl: Playlist) => {
    setSelectedPlaylist(pl);
    setActiveTab("playlist");
    try {
      const tracks = await playlists.loadPlaylistTracks(pl);
      search.setPageResults(tracks);
      search.setPageQuery(`Playlist: ${pl.name}`);
    } catch {
      search.setPageResults([]);
    }
  };

  const goHome = () => {
    setActiveTab("home");
    search.clearSearch();
  };

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="app-shell">
      {/* ══ HEADER ══════════════════════════════════════════════════════════ */}
      <header className="app-header">
        <div className="header-logo" onClick={goHome} style={{ cursor: "pointer" }}>
          <img src="/logo.png" alt="Ammy" className="brand-logo-img" />
          <span>Ammy AI</span>
        </div>

        <div className="header-center">
          <SearchBar
            query={search.searchQuery}
            onQueryChange={search.handleQueryChange}
            onSubmit={handleSearchSubmit}
            dropdownResults={search.dropdownResults}
            showDropdown={search.showDropdown}
            setShowDropdown={search.setShowDropdown}
            onSelectCandidate={player.handlePlayTrack}
          />
        </div>

        <div className="header-right">
          <button
            id="import-btn"
            className="header-import-btn"
            title="Import a local audio file"
            onClick={() => setShowImportModal(true)}
          >
            <ImportIcon />
            <span className="header-import-label">Import</span>
          </button>
        </div>
      </header>

      {/* ══ BODY ════════════════════════════════════════════════════════════ */}
      <div className="app-body">
        <Sidebar
          history={history}
          activeFilename={result?.filename ?? null}
          user={auth.user}
          onLoginSuccess={auth.handleLoginSuccess}
          onLogout={auth.handleLogout}
          onSelect={(h) => { setResult(h); setActiveTab("analysis"); setError(null); }}
          onHome={goHome}
          onAnalysisClick={() => setActiveTab("analysis")}
          activeTab={activeTab}
          playlists={playlists.playlists}
          onShowCreatePlaylist={() => setShowCreatePlaylistModal(true)}
          onSelectPlaylist={handleSelectPlaylist}
        />

        <main className="app-main">
          <div className={`main-center ${activeTab === "home" ? "main-center--wide" : ""}`}>
            {/* 1. HOME */}
            {activeTab === "home" && (
              <HomeView
                recentTracks={player.recentTracks}
                playlists={playlists.playlists}
                onPlayTrack={player.handlePlayTrack}
                onSelectPlaylist={handleSelectPlaylist}
              />
            )}

            {/* 2. SEARCH RESULTS */}
            {activeTab === "search" && (
              <SearchResults
                pageQuery={search.pageQuery}
                pageResults={search.pageResults}
                isSearching={search.isSearching}
                searchError={search.searchError}
                playingTrackId={player.playingTrack?.id ?? null}
                likedTrackIds={playlists.likedTrackIds}
                onPlayTrack={player.handlePlayTrack}
                onAnalyze={handleSelectCandidate}
                onToggleLike={playlists.handleToggleLike}
              />
            )}

            {/* 3. ANALYSIS */}
            {activeTab === "analysis" && (
              <div className="nm-analysis-view fade-in">
                {isProcessing ? (
                  <div className="nm-card nm-processing">
                    <div className="nm-spinner"></div>
                    <div className="nm-processing-title">{processingLabel}</div>
                    <div className="nm-processing-sub">Extracting vibe, genre and emotion features...</div>
                  </div>
                ) : result ? (
                  <AnalysisView
                    result={result}
                    showBackButton={false}
                    onBack={() => setActiveTab("search")}
                    onNewSearch={goHome}
                  />
                ) : (
                  <div className="nm-card welcome-card">
                    <div className="nm-icon-circle"><SparklesIcon /></div>
                    <div className="nm-drop-title">No analysis yet</div>
                    <div className="nm-drop-sub">
                      Pick a track and click <strong>Analyze Track</strong> in the player to see its vibe here!
                    </div>
                  </div>
                )}
                {error && (
                  <div className="nm-card nm-error-card fade-in" style={{ marginTop: "20px" }}>
                    <div className="nm-error">{error}</div>
                    <button className="nm-btn" style={{ marginTop: "1rem" }} onClick={() => setError(null)}>
                      Dismiss
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* 4. PLAYLIST */}
            {activeTab === "playlist" && selectedPlaylist && (
              <PlaylistView
                playlist={selectedPlaylist}
                tracks={search.pageResults}
                playingTrackId={player.playingTrack?.id ?? null}
                onPlayTrack={player.handlePlayTrack}
              />
            )}
          </div>
        </main>
      </div>

      {/* ══ MODALS ══════════════════════════════════════════════════════════ */}
      <ImportModal
        show={showImportModal}
        onClose={() => setShowImportModal(false)}
        onFileSelected={handleFileSelected}
      />
      <CreatePlaylistModal
        show={showCreatePlaylistModal}
        onClose={() => setShowCreatePlaylistModal(false)}
        onSubmit={playlists.handleCreatePlaylist}
      />

      {/* ══ AUDIO PLAYER ════════════════════════════════════════════════════ */}
      {player.playingTrack && (
        <Player
          track={player.playingTrack}
          playlist={search.pageResults.length > 0 ? search.pageResults : player.recentTracks}
          playlists={playlists.playlists}
          onTrackChange={player.handlePlayTrack}
          onAnalyze={() => handleSelectCandidate(player.playingTrack!)}
          likedTrackIds={playlists.likedTrackIds}
          onToggleLike={playlists.handleToggleLike}
          onAddToPlaylist={playlists.handleAddToPlaylist}
        />
      )}
    </div>
  );
}

export default App;
