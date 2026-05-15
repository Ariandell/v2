// ── Shared TypeScript Interfaces ─────────────────────────────────────────────

export interface Prediction {
  genre: string;
  probability: number;
}

export interface Vibes {
  vibe_1?: string;
  score_1?: number;
  vibe_2?: string;
  score_2?: number;
}

export interface AnalysisResult {
  filename: string;
  predictions: Prediction[];
  language: string;
  is_instrumental: boolean;
  lyrics_english: string;
  vibes: Vibes;
}

export interface SearchCandidate {
  id: string;
  url: string;
  title: string;
  uploader: string;
  duration: string;
  thumbnail: string;
}

export interface UserInfo {
  name: string;
  email: string;
  picture: string;
}

export interface Playlist {
  id: number;
  name: string;
  is_liked_playlist: boolean;
  created_at: string;
  track_count: number;
}
