"use client";

import { useState } from "react";
import { Search, Link2, AtSign, Music } from 'lucide-react';
import { RadarSpinner } from '@/components/ui/radar-loader';
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";

export type InputType = "NAME" | "SPOTIFY_URL" | "SPOTIFY_ID" | "VIBERATE_URL";

interface SearchBarProps {
  onSearch: (query: string, inputType: InputType) => void;
  isLoading?: boolean;
  placeholder?: string;
}

const INPUT_TYPE_OPTIONS = [
  { value: "NAME", label: "Nom d'artiste", icon: AtSign },
  { value: "SPOTIFY_URL", label: "URL Spotify", icon: Link2 },
  { value: "SPOTIFY_ID", label: "ID Spotify", icon: Music },
  { value: "VIBERATE_URL", label: "URL Viberate", icon: Link2 },
];

export function SearchBar({
  onSearch,
  isLoading = false,
  placeholder = "Rechercher un artiste...",
}: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [inputType, setInputType] = useState<InputType>("NAME");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim().length >= 2) {
      onSearch(query.trim(), inputType);
    }
  };

  const detectInputType = (value: string): InputType => {
    if (value.includes("open.spotify.com")) return "SPOTIFY_URL";
    if (value.includes("viberate.com")) return "VIBERATE_URL";
    if (/^[0-9a-zA-Z]{22}$/.test(value)) return "SPOTIFY_ID";
    return "NAME";
  };

  const handleInputChange = (value: string) => {
    setQuery(value);
    // Auto-detect input type
    const detected = detectInputType(value);
    if (detected !== "NAME") {
      setInputType(detected);
    }
  };

  const SelectedIcon = INPUT_TYPE_OPTIONS.find((o) => o.value === inputType)?.icon || AtSign;

  return (
    <Card className="w-full">
      <CardContent className="p-3">
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          {/* Input type selector */}
          <Select
            value={inputType}
            onValueChange={(v) => setInputType(v as InputType)}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue>
                <div className="flex items-center gap-2">
                  <SelectedIcon className="h-4 w-4" />
                  <span className="hidden sm:inline">
                    {INPUT_TYPE_OPTIONS.find((o) => o.value === inputType)?.label}
                  </span>
                </div>
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {INPUT_TYPE_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  <div className="flex items-center gap-2">
                    <option.icon className="h-4 w-4" />
                    {option.label}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Search input */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              value={query}
              onChange={(e) => handleInputChange(e.target.value)}
              placeholder={placeholder}
              className="pl-9"
              disabled={isLoading}
            />
          </div>

          {/* Submit button */}
          <Button type="submit" disabled={isLoading || query.trim().length < 2}>
            {isLoading ? (
              <>
                <RadarSpinner className="h-4 w-4 mr-2 animate-spin" />
                Recherche...
              </>
            ) : (
              <>
                <Search className="h-4 w-4 mr-2" />
                Rechercher
              </>
            )}
          </Button>
        </form>

        {/* Help text */}
        <p className="text-xs text-muted-foreground mt-2">
          {inputType === "NAME" && "Entrez le nom de l'artiste (minimum 2 caractères)"}
          {inputType === "SPOTIFY_URL" && "Collez l'URL Spotify de l'artiste"}
          {inputType === "SPOTIFY_ID" && "Entrez l'ID Spotify (22 caractères)"}
          {inputType === "VIBERATE_URL" && "Collez l'URL Viberate de l'artiste"}
        </p>
      </CardContent>
    </Card>
  );
}
