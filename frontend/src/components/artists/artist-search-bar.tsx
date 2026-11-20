"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  Search,
  Music2,
  Sparkles,
  ExternalLink,
  Check,
  AlertCircle,
  Database,
} from 'lucide-react';
import { RadarSpinner } from '@/components/ui/radar-loader';
import { cn } from "@/lib/utils";

// Custom debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// Spotify icon
const SpotifyIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
  </svg>
);

interface AutocompleteItem {
  artist_id: string | null;
  display_name: string;
  avatar_url: string | null;
  sources: string[];
  viberate_url: string | null;
  spotify_artist_id: string | null;
  monthly_listeners: number | null;
  genre: string | null;
  country: string | null;
  status: "NEW" | "ANALYZED";
  data_quality: string | null;
  last_enriched_at: string | null;
  score: number | null;
}

interface ArtistSearchBarProps {
  onAnalyze: (resolved: Record<string, any>) => void;
  isAnalyzing?: boolean;
  placeholder?: string;
}

function detectInputType(input: string): "NAME" | "VIBERATE_URL" | "SPOTIFY_URL" {
  const lower = input.toLowerCase().trim();
  if (lower.includes("viberate.com/artist/")) {
    return "VIBERATE_URL";
  }
  if (lower.includes("spotify.com/artist/") || /^[a-zA-Z0-9]{22}$/.test(input.trim())) {
    return "SPOTIFY_URL";
  }
  return "NAME";
}

function formatNumber(n: number | null | undefined): string {
  if (!n) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return n.toString();
}

export function ArtistSearchBar({ onAnalyze, isAnalyzing, placeholder }: ArtistSearchBarProps) {
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebounce(query, 300);
  const [isOpen, setIsOpen] = useState(false);
  const [items, setItems] = useState<AutocompleteItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Fetch autocomplete
  useEffect(() => {
    async function fetchAutocomplete() {
      if (debouncedQuery.length < 2) {
        setItems([]);
        return;
      }

      setIsLoading(true);
      try {
        const response = await api.get(`/api/v1/artists/autocomplete?q=${encodeURIComponent(debouncedQuery)}&limit=8`);
        setItems(response.data.items || []);
        setIsOpen(true);
        setSelectedIndex(-1);
      } catch (error) {
        console.error("Autocomplete error:", error);
        setItems([]);
      } finally {
        setIsLoading(false);
      }
    }

    fetchAutocomplete();
  }, [debouncedQuery]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!isOpen) return;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setSelectedIndex(prev => Math.min(prev + 1, items.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIndex(prev => Math.max(prev - 1, -1));
        break;
      case "Enter":
        e.preventDefault();
        if (selectedIndex >= 0 && items[selectedIndex]) {
          handleSelect(items[selectedIndex]);
        } else if (query.trim()) {
          handleSubmit();
        }
        break;
      case "Escape":
        setIsOpen(false);
        break;
    }
  }, [isOpen, selectedIndex, items, query]);

  // Select from autocomplete
  const handleSelect = (item: AutocompleteItem) => {
    setQuery(item.display_name);
    setIsOpen(false);
    
    // If already analyzed, could navigate to detail
    // For now, trigger new analysis with available data
    onAnalyze({
      display_name: item.display_name,
      viberate_url: item.viberate_url,
      spotify_artist_id: item.spotify_artist_id,
      artist_id: item.artist_id,
      input_type: item.viberate_url ? "VIBERATE_URL" : item.spotify_artist_id ? "SPOTIFY_URL" : "NAME",
    });
  };

  // Submit for search/analyze
  const handleSubmit = async () => {
    if (!query.trim()) return;
    
    const inputType = detectInputType(query);
    const inputValue = query.trim();

    try {
      const response = await api.post("/api/v1/artists/search", {
        input_type: inputType,
        input_value: inputValue,
      });

      const data = response.data;

      if (data.status === "FOUND" && data.artist_id) {
        // Artist exists - could navigate or refresh
        onAnalyze({
          artist_id: data.artist_id,
          input_type: inputType,
          display_name: inputValue,
        });
      } else if (data.status === "RESOLVED" && data.can_analyze) {
        // New artist - trigger analysis
        onAnalyze(data.resolved);
      } else if (data.status === "NEED_SELECTION" && data.candidates) {
        // Show candidates in dropdown
        setItems(data.candidates.map((c: any) => ({
          artist_id: null,
          display_name: c.display_name,
          avatar_url: c.avatar_url,
          sources: [c.source],
          viberate_url: c.viberate_url,
          spotify_artist_id: c.spotify_artist_id,
          monthly_listeners: null,
          genre: null,
          country: null,
          status: "NEW",
          data_quality: null,
          last_enriched_at: null,
          score: null,
        })));
        setIsOpen(true);
      }
    } catch (error) {
      console.error("Search error:", error);
    }
  };

  // Close on click outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        listRef.current &&
        !listRef.current.contains(e.target as Node) &&
        !inputRef.current?.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative w-full max-w-3xl mx-auto">
      {/* Search Input */}
      <div className="relative group">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          {isLoading ? (
            <RadarSpinner className="h-5 w-5 text-muted-foreground animate-spin" />
          ) : (
            <Search className="h-5 w-5 text-muted-foreground group-focus-within:text-primary transition-colors" />
          )}
        </div>
        <Input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => items.length > 0 && setIsOpen(true)}
          placeholder={placeholder || "Nom d'artiste, URL Viberate ou Spotify…"}
          className="pl-12 pr-28 h-14 text-lg rounded-2xl border-2 shadow-sm focus:shadow-md focus:border-primary transition-all"
          disabled={isAnalyzing}
        />
        <div className="absolute inset-y-0 right-0 pr-2 flex items-center gap-2">
          <Button
            onClick={handleSubmit}
            disabled={!query.trim() || isAnalyzing}
            className="h-10 px-5 rounded-xl"
          >
            {isAnalyzing ? (
              <RadarSpinner className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Sparkles className="h-4 w-4 mr-2" />
            )}
            Analyser
          </Button>
        </div>
      </div>

      {/* Autocomplete Dropdown */}
      {isOpen && items.length > 0 && (
        <div
          ref={listRef}
          className="absolute top-full left-0 right-0 mt-2 bg-background border rounded-xl shadow-lg z-50 overflow-hidden"
        >
          <div className="py-2 max-h-[400px] overflow-y-auto">
            {items.map((item, index) => (
              <div
                key={`${item.display_name}-${index}`}
                onClick={() => handleSelect(item)}
                className={cn(
                  "flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors",
                  index === selectedIndex
                    ? "bg-accent"
                    : "hover:bg-accent/50"
                )}
              >
                {/* Avatar */}
                <Avatar className="h-10 w-10">
                  <AvatarImage src={item.avatar_url || undefined} alt={item.display_name} />
                  <AvatarFallback>
                    <Music2 className="h-4 w-4" />
                  </AvatarFallback>
                </Avatar>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{item.display_name}</span>
                    {item.status === "ANALYZED" && (
                      <Badge variant="secondary" className="text-xs">
                        <Check className="h-3 w-3 mr-1" />
                        Analysé
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    {item.genre && <span>{item.genre}</span>}
                    {item.monthly_listeners && (
                      <>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <SpotifyIcon className="h-3 w-3 text-green-500" />
                          {formatNumber(item.monthly_listeners)}
                        </span>
                      </>
                    )}
                    {item.score && (
                      <>
                        <span>•</span>
                        <span className="font-medium text-primary">{item.score}/100</span>
                      </>
                    )}
                  </div>
                </div>

                {/* Source badges */}
                <div className="flex items-center gap-1">
                  {item.sources.includes("DB") && (
                    <Badge variant="outline" className="text-xs">
                      <Database className="h-3 w-3 mr-1" />
                      Cache
                    </Badge>
                  )}
                  {item.viberate_url && (
                    <Badge variant="outline" className="text-xs bg-purple-500/10 text-purple-600 border-purple-200">
                      VB
                    </Badge>
                  )}
                  {item.spotify_artist_id && (
                    <Badge variant="outline" className="text-xs bg-green-500/10 text-green-600 border-green-200">
                      <SpotifyIcon className="h-3 w-3" />
                    </Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
