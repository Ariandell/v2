import { useState } from "react";
import { CloseIcon, ListIcon } from "../shared/Icons";

interface Props {
  show: boolean;
  onClose: () => void;
  onSubmit: (name: string) => void;
}

export default function CreatePlaylistModal({ show, onClose, onSubmit }: Props) {
  const [name, setName] = useState("");

  if (!show) return null;

  const handleSubmit = () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
    setName("");
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 400 }}>
        <div className="modal-header">
          <div className="modal-header-title">
            <ListIcon /> Create Playlist
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <CloseIcon />
          </button>
        </div>
        <div style={{ padding: "20px 24px" }}>
          <label style={{ 
            display: "block", 
            fontSize: "12px", 
            fontWeight: 600, 
            color: "var(--text3)", 
            marginBottom: "8px",
            textTransform: "uppercase",
            letterSpacing: "0.05em"
          }}>
            Playlist name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(); }}
            placeholder="My awesome playlist..."
            autoFocus
            style={{
              width: "100%",
              padding: "10px 14px",
              fontSize: "14px",
              border: "1px solid var(--border)",
              borderRadius: "6px",
              background: "var(--bg)",
              color: "var(--text)",
              outline: "none",
              boxSizing: "border-box",
              transition: "border-color 0.2s",
            }}
          />
          <div style={{ display: "flex", gap: "10px", marginTop: "20px", justifyContent: "flex-end" }}>
            <button
              onClick={onClose}
              style={{
                padding: "8px 18px",
                fontSize: "13px",
                fontWeight: 600,
                border: "1px solid var(--border)",
                borderRadius: "6px",
                background: "transparent",
                color: "var(--text2)",
                cursor: "pointer",
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={!name.trim()}
              style={{
                padding: "8px 18px",
                fontSize: "13px",
                fontWeight: 600,
                border: "none",
                borderRadius: "6px",
                background: name.trim() ? "var(--text)" : "var(--border)",
                color: name.trim() ? "var(--bg)" : "var(--text3)",
                cursor: name.trim() ? "pointer" : "not-allowed",
                transition: "all 0.2s",
              }}
            >
              Create
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
