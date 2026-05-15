import { useRef, DragEvent, useState } from "react";
import { MusicNoteIcon, CloseIcon } from "../shared/Icons";

interface Props {
  show: boolean;
  onClose: () => void;
  onFileSelected: (file: File) => void;
}

export default function ImportModal({ show, onClose, onFileSelected }: Props) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!show) return null;

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };
  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.[0]) onFileSelected(e.dataTransfer.files[0]);
  };
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) onFileSelected(e.target.files[0]);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span>Import local file</span>
          <button className="modal-close-btn" onClick={onClose}>
            <CloseIcon />
          </button>
        </div>
        <div
          className={`nm-drop${isDragging ? " dragging" : ""}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            type="file"
            style={{ display: "none" }}
            accept=".mp3,.wav,.flac"
            ref={fileInputRef}
            onChange={handleFileChange}
          />
          <div className="nm-icon-circle">
            <MusicNoteIcon />
          </div>
          <div className="nm-drop-title">Drop your track here</div>
          <div className="nm-drop-sub">or click to browse — MP3, WAV, FLAC</div>
          <div className="nm-pills">
            <span className="nm-pill">MP3</span>
            <span className="nm-pill">WAV</span>
            <span className="nm-pill">FLAC</span>
          </div>
        </div>
      </div>
    </div>
  );
}
