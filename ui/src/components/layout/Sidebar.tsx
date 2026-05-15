import { GoogleLogin } from "@react-oauth/google";
import { HistoryIcon, MusicNoteIcon, HomeIcon, ListIcon, HeartFilledIcon, SparklesIcon } from "../shared/Icons";
import type { AnalysisResult, UserInfo, Playlist } from "../../types";

interface Props {
  history: AnalysisResult[];
  activeFilename: string | null;
  user: UserInfo | null;
  onLoginSuccess: (res: any) => void;
  onLogout: () => void;
  onSelect: (item: AnalysisResult) => void;
  onHome: () => void;
  onAnalysisClick: () => void;
  activeTab: string;
  playlists: Playlist[];
  onShowCreatePlaylist: () => void;
  onSelectPlaylist: (pl: Playlist) => void;
}

export default function Sidebar({
  history,
  activeFilename,
  user,
  onLoginSuccess,
  onLogout,
  onSelect,
  onHome,
  onAnalysisClick,
  activeTab,
  playlists,
  onShowCreatePlaylist,
  onSelectPlaylist,
}: Props) {
  return (
    <aside className="app-sidebar">
      {/* ── User Section ── */}
      <div className="sidebar-user-section">
        {user ? (
          <div className="sidebar-profile">
            <img src={user.picture} alt="" className="profile-img" />
            <div className="profile-info">
              <div className="profile-name">{user.name}</div>
              <button className="logout-btn" onClick={onLogout}>
                Logout
              </button>
            </div>
          </div>
        ) : (
          <div className="login-wrapper">
            <GoogleLogin
              onSuccess={onLoginSuccess}
              onError={() => console.log("Login Failed")}
              useOneTap
              theme="outline"
              shape="pill"
              size="medium"
              width="170px"
            />
          </div>
        )}
      </div>

      {/* ── Library / Home ── */}
      <div style={{ marginBottom: "16px" }}>
        <button 
          className={`sidebar-item ${activeTab === "home" ? "sidebar-item--active" : ""}`} 
          onClick={onHome}
        >
          <div className="sidebar-item-icon">
            <HomeIcon />
          </div>
          <div className="sidebar-item-text">
            <div className="sidebar-item-name">Home</div>
          </div>
        </button>

        <button 
          className={`sidebar-item ${activeTab === "analysis" ? "sidebar-item--active" : ""}`} 
          onClick={onAnalysisClick}
        >
          <div className="sidebar-item-icon">
            <SparklesIcon />
          </div>
          <div className="sidebar-item-text">
            <div className="sidebar-item-name">Vibe Analysis</div>
          </div>
        </button>
      </div>

      <div className="sidebar-section-label">Playlists</div>
      <button 
        className="sidebar-create-btn" 
        onClick={onShowCreatePlaylist}
      >
        <span>+</span> New Playlist
      </button>

      {playlists.filter(pl => !pl.is_liked_playlist || pl.track_count > 0).map((pl) => (
        <button
          key={pl.id}
          className="sidebar-item"
          onClick={() => onSelectPlaylist(pl)}
        >
          <div className="sidebar-item-icon">
            {pl.is_liked_playlist ? <HeartFilledIcon /> : <ListIcon />}
          </div>
          <div className="sidebar-item-text">
            <div className="sidebar-item-name">{pl.name}</div>
            <div className="sidebar-item-genre">{pl.track_count} tracks</div>
          </div>
        </button>
      ))}

      <div style={{ height: "24px" }} />

      <div className="sidebar-section-label">
        <HistoryIcon /> Recent
      </div>
      {history.length === 0 && (
        <div className="sidebar-empty">No tracks yet</div>
      )}
      {history.map((h, i) => (
        <button
          key={i}
          className={`sidebar-item${
            activeFilename === h.filename && i === 0
              ? " sidebar-item--active"
              : ""
          }`}
          onClick={() => onSelect(h)}
        >
          <div className="sidebar-item-icon">
            <MusicNoteIcon />
          </div>
          <div className="sidebar-item-text">
            <div className="sidebar-item-name">{h.filename}</div>
            <div className="sidebar-item-genre">
              {h.predictions[0]?.genre ?? "—"}
            </div>
          </div>
        </button>
      ))}
    </aside>
  );
}
