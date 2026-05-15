import { useRef } from "react";
import type { SearchCandidate } from "../../types";
import { SearchIcon, CloseIcon } from "../shared/Icons";

interface Props {
  query: string;
  onQueryChange: (val: string) => void;
  onSubmit: () => void;
  dropdownResults: SearchCandidate[];
  showDropdown: boolean;
  setShowDropdown: (v: boolean) => void;
  onSelectCandidate: (c: SearchCandidate) => void;
}

export default function SearchBar({
  query,
  onQueryChange,
  onSubmit,
  dropdownResults,
  showDropdown,
  setShowDropdown,
  onSelectCandidate,
}: Props) {
  const isInputFocused = useRef(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  return (
    <form className="header-search-wrap" onSubmit={handleSubmit}>
      <div className="header-search-box">
        <span className="search-icon-inner"><SearchIcon /></span>
        <input
          id="main-search"
          className="header-search-input"
          type="text"
          placeholder="Search a song on YouTube..."
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onBlur={() => {
            isInputFocused.current = false;
            setTimeout(() => setShowDropdown(false), 150);
          }}
          onFocus={() => {
            isInputFocused.current = true;
            if (dropdownResults.length > 0) setShowDropdown(true);
          }}
          autoComplete="off"
        />
        {query && (
          <button type="button" className="search-clear-btn" onClick={() => onQueryChange("")}>
            <CloseIcon />
          </button>
        )}
      </div>

      {/* Dropdown — only when typing, not after Enter */}
      {showDropdown && dropdownResults.length > 0 && (
        <div className="search-dropdown">
          {dropdownResults.map((c) => (
            <button
              key={c.id}
              className="search-dd-item search-dd-result"
              type="button"
              onMouseDown={() => onSelectCandidate(c)}
            >
              {c.thumbnail && <img className="search-dd-thumb" src={c.thumbnail} alt="" />}
              <div className="search-dd-meta">
                <div className="search-dd-title">{c.title}</div>
                <div className="search-dd-sub">{c.uploader} · {c.duration}</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </form>
  );
}
