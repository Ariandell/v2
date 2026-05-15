import type { SearchCandidate, AnalysisResult, UserInfo, Playlist } from "./types";

const API = "http://localhost:8000";

// ── Search ──────────────────────────────────────────────────────────────────

export async function fetchSearch(
  q: string,
  count: number = 5
): Promise<SearchCandidate[]> {
  if (!q.trim()) return [];
  const res = await fetch(
    `${API}/search?q=${encodeURIComponent(q)}&count=${count}`
  );
  if (!res.ok) throw new Error(`Search failed: ${res.status}`);
  const data = await res.json();
  return data.results || [];
}

// ── History Sync ────────────────────────────────────────────────────────────

export async function syncHistory(
  track: SearchCandidate,
  user: UserInfo
): Promise<void> {
  try {
    await fetch(`${API}/sync-history`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...track,
        user_email: user.email,
        user_name: user.name,
        user_picture: user.picture,
      }),
    });
  } catch (err) {
    console.error("Failed to sync history:", err);
  }
}

export async function fetchRecentTracks(
  email: string
): Promise<SearchCandidate[]> {
  try {
    const res = await fetch(
      `${API}/recent-tracks?email=${encodeURIComponent(email)}`
    );
    if (!res.ok) return [];
    const data = await res.json();
    return data.results || [];
  } catch {
    return [];
  }
}

// ── Playlists ───────────────────────────────────────────────────────────────

export async function fetchPlaylists(email: string): Promise<Playlist[]> {
  const res = await fetch(`${API}/playlists?email=${encodeURIComponent(email)}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.playlists || [];
}

export async function createPlaylist(name: string, email: string): Promise<void> {
  await fetch(`${API}/playlists`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, user_email: email })
  });
}

export async function fetchPlaylistTracks(playlistId: number, email: string): Promise<SearchCandidate[]> {
  const res = await fetch(`${API}/playlists/${playlistId}/tracks?email=${encodeURIComponent(email)}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.results || [];
}

export async function addTrackToPlaylist(playlistId: number, track: SearchCandidate, email: string): Promise<void> {
  await fetch(`${API}/playlists/${playlistId}/tracks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...track, user_email: email })
  });
}

export async function removeTrackFromPlaylist(playlistId: number, trackId: string, email: string): Promise<void> {
  await fetch(`${API}/playlists/${playlistId}/tracks/${encodeURIComponent(trackId)}?email=${encodeURIComponent(email)}`, {
    method: "DELETE"
  });
}

// ── Analyze by URL ──────────────────────────────────────────────────────────

export async function analyzeUrl(
  url: string,
  title: string
): Promise<AnalysisResult> {
  const res = await fetch(`${API}/analyze_url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, title }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || `Server error ${res.status}`);
  }
  return res.json();
}

// ── Analyze by file upload ──────────────────────────────────────────────────

export async function analyzeFile(file: File): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API}/analyze`, { method: "POST", body: formData });
  if (!res.ok)
    throw new Error(`Server returned ${res.status} ${res.statusText}`);
  return res.json();
}

// ── Stream URL helper ───────────────────────────────────────────────────────

export function streamUrl(videoId: string): string {
  return `${API}/stream/${videoId}`;
}

// ── Prefetch — pre-download audio for faster playback ───────────────────────

export function prefetchTracks(ids: string[]): void {
  if (ids.length === 0) return;
  fetch(`${API}/prefetch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids: ids.slice(0, 3) }),
  }).catch(() => {
    /* fire-and-forget — don't block on prefetch failures */
  });
}
