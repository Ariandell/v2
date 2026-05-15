/**
 * useSearch — YouTube search with debounced autocomplete + full search.
 */

import { useState, useRef, useCallback } from "react";
import type { SearchCandidate } from "../types";
import { fetchSearch, prefetchTracks } from "../api";

export function useSearch() {
  const [searchQuery, setSearchQuery] = useState("");
  const [dropdownResults, setDropdownResults] = useState<SearchCandidate[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [pageResults, setPageResults] = useState<SearchCandidate[]>([]);
  const [pageQuery, setPageQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /** Debounced autocomplete on every keystroke */
  const handleQueryChange = useCallback((val: string) => {
    setSearchQuery(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!val.trim()) {
      setDropdownResults([]);
      setShowDropdown(false);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      try {
        const results = await fetchSearch(val, 5);
        setDropdownResults(results);
        setShowDropdown(true);
      } catch {
        /* silently ignore dropdown errors */
      }
    }, 250);
  }, []);

  /** Full search on Enter press */
  const handleSearchSubmit = useCallback(async () => {
    const q = searchQuery.trim();
    if (!q) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setShowDropdown(false);

    const prefill = dropdownResults.length > 0 ? dropdownResults : [];
    setPageResults(prefill);
    setDropdownResults([]);
    setPageQuery(q);
    setIsSearching(true);
    setSearchError(null);

    try {
      const results = await fetchSearch(q, 20);
      setPageResults(results);

      // Pre-download audio for top 3 results so playback is instant
      prefetchTracks(results.slice(0, 3).map((r) => r.id));
    } catch (err: any) {
      setSearchError(err.message || "Search failed");
    } finally {
      setIsSearching(false);
    }
  }, [searchQuery, dropdownResults]);

  /** Reset search to go back home */
  const clearSearch = () => {
    setPageResults([]);
    setPageQuery("");
    setSearchQuery("");
    setDropdownResults([]);
    setShowDropdown(false);
  };

  return {
    searchQuery,
    dropdownResults,
    showDropdown,
    setShowDropdown,
    pageResults,
    setPageResults,
    pageQuery,
    setPageQuery,
    isSearching,
    searchError,
    handleQueryChange,
    handleSearchSubmit,
    clearSearch,
  };
}
