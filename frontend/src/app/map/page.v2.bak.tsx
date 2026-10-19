"use client";
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState, useMemo, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import {
  MapPin,
  Music,
  Tent,
  Store,
  Sparkles,
  Calendar,
  Users,
  Filter,
  X,
  Loader2,
  Search,
  Eye,
  RefreshCw,
} from "lucide-react";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// Types
interface ArtistEvent {
  id: string;
  artist_name: string;
  artist_id: string;
  artist_image: string | null;
  artist_score: number;
  artist_genres: string[];
  monthly_listeners: number;
  event_type: "concert" | "festival" | "popup_store" | "brand_event";
  event_type_label: string;
  venue: string;
  city: string;
  lat: number;
  lng: number;
  date: string;
  date_label: string;
  capacity: number | null;
  price_min: number;
  price_max: number;
  fee_estimate_min?: number | null;
  fee_estimate_max?: number | null;
  has_contact?: boolean;
}

interface EventsResponse {
  events: ArtistEvent[];
  total: number;
  stats: {
    by_type: Record<string, number>;
    by_city: Record<string, number>;
    total_artists: number;
  };
  cities: string[];
  source?: "ticketmaster" | "generated";
}

// API
const eventsMapApi = {
  getEvents: async (params: {
    event_type?: string;
    city?: string;
    artist?: string;
    score_min?: number;
    date_from?: string;
    date_to?: string;
  }): Promise<EventsResponse> => {
    const token = localStorage.getItem("token");
    const queryParams = new URLSearchParams();
    if (params.event_type && params.event_type !== "all")
      queryParams.append("event_type", params.event_type);
    if (params.city && params.city !== "all")
      queryParams.append("city", params.city);
    if (params.artist) queryParams.append("artist", params.artist);
    if (params.score_min !== undefined && params.score_min > 0)
      queryParams.append("score_min", String(params.score_min));
    if (params.date_from) queryParams.append("date_from", params.date_from);
    if (params.date_to) queryParams.append("date_to", params.date_to);

    const response = await workspaceFetch(
      `/api/v1/map/artist-events?${queryParams}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    if (!response.ok) {
      throw new Error("Erreur chargement événements");
    }

    return response.json();
  },

  syncEvents: async (): Promise<{ status: string; task_id?: string; message?: string }> => {
    const token = localStorage.getItem("token");
    const response = await workspaceFetch("/api/v1/map/sync-events", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.json();
  },
};

// Event type config
const EVENT_TYPES: Record<string, {
  label: string;
  icon: typeof Music;
  color: string;
  bgColor: string;
  lightBg: string;
  textColor: string;
  borderColor: string;
}> = {
  concert: {
    label: "Concerts",
    icon: Music,
    color: "#6366f1",
    bgColor: "bg-indigo-500",
    lightBg: "bg-indigo-50",
    textColor: "text-indigo-700",
    borderColor: "border-indigo-200",
  },
  festival: {
    label: "Festivals",
    icon: Tent,
    color: "#f59e0b",
    bgColor: "bg-amber-500",
    lightBg: "bg-amber-50",
    textColor: "text-amber-700",
    borderColor: "border-amber-200",
  },
  popup_store: {
    label: "Pop-up Stores",
    icon: Store,
    color: "#10b981",
    bgColor: "bg-emerald-500",
    lightBg: "bg-emerald-50",
    textColor: "text-emerald-700",
    borderColor: "border-emerald-200",
  },
  brand_event: {
    label: "Événements de marque",
    icon: Sparkles,
    color: "#ec4899",
    bgColor: "bg-pink-500",
    lightBg: "bg-pink-50",
    textColor: "text-pink-700",
    borderColor: "border-pink-200",
  },
};

// Dynamic import of the map component (Leaflet needs window)
const MapView = dynamic(() => import("./MapView"), {
  ssr: false,
  loading: () => (
    <div className="h-[600px] bg-muted rounded-xl flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">
          Chargement de la carte...
        </span>
      </div>
    </div>
  ),
});

function formatListeners(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

// Event card component
function EventCard({
  event,
  onSelect,
  isSelected,
}: {
  event: ArtistEvent;
  onSelect: (e: ArtistEvent) => void;
  isSelected: boolean;
}) {
  const config = EVENT_TYPES[event.event_type] || EVENT_TYPES.concert;
  const Icon = config.icon;
  const eventDate = new Date(event.date);
  const isUpcoming =
    eventDate > new Date() &&
    eventDate < new Date(Date.now() + 30 * 86400000);

  const scoreColor =
    event.artist_score >= 70
      ? "bg-green-100 text-green-700"
      : event.artist_score >= 40
      ? "bg-amber-100 text-amber-700"
      : "bg-gray-100 text-gray-600";

  const feeLabel =
    event.fee_estimate_min && event.fee_estimate_max
      ? `${Math.round(event.fee_estimate_min / 1000)}–${Math.round(event.fee_estimate_max / 1000)}k€`
      : null;

  return (
    <button
      onClick={() => onSelect(event)}
      className={`w-full text-left p-3 rounded-lg border transition-all hover:shadow-md ${
        isSelected
          ? `${config.lightBg} ${config.borderColor} border-2 shadow-md`
          : "bg-card border-border hover:border-muted-foreground/30"
      }`}
    >
      <div className="flex items-start gap-3">
        {event.artist_image ? (
          <img
            src={event.artist_image}
            alt={event.artist_name}
            className="w-10 h-10 rounded-full object-cover flex-shrink-0"
          />
        ) : (
          <div
            className={`w-10 h-10 rounded-full ${config.bgColor} flex items-center justify-center flex-shrink-0`}
          >
            <Icon className="h-5 w-5 text-white" />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-sm truncate">
            {event.artist_name}
          </p>
          <p className="text-xs text-muted-foreground truncate">
            {event.venue}
          </p>
          <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
            <Badge
              variant="secondary"
              className={`text-[10px] px-1.5 py-0 ${config.lightBg} ${config.textColor}`}
            >
              <Icon className="h-3 w-3 mr-0.5" />
              {config.label}
            </Badge>
            {event.artist_score > 0 && (
              <Badge variant="secondary" className={`text-[10px] px-1.5 py-0 ${scoreColor}`}>
                {event.artist_score}
              </Badge>
            )}
            {feeLabel && (
              <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                {feeLabel}
              </Badge>
            )}
            {event.has_contact === false && (
              <Badge variant="outline" className="text-[10px] px-1.5 py-0 border-orange-300 text-orange-600">
                Contact ?
              </Badge>
            )}
            {isUpcoming && (
              <Badge
                variant="secondary"
                className="text-[10px] px-1.5 py-0 bg-red-50 text-red-600"
              >
                Bientôt
              </Badge>
            )}
          </div>
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-xs font-medium">{event.date_label}</p>
          <p className="text-[10px] text-muted-foreground">{event.city}</p>
        </div>
      </div>
    </button>
  );
}

function MapContent() {
  const [eventType, setEventType] = useState("all");
  const [city, setCity] = useState("all");
  const [artistSearch, setArtistSearch] = useState("");
  const [scoreMin, setScoreMin] = useState(0);
  const [period, setPeriod] = useState("all");
  const [selectedEvent, setSelectedEvent] = useState<ArtistEvent | null>(null);
  const [activeTypes, setActiveTypes] = useState<Set<string>>(
    new Set(["concert", "festival", "popup_store", "brand_event"])
  );

  const periodDates = useMemo(() => {
    if (period === "all") return {};
    const now = new Date();
    const from = now.toISOString().slice(0, 10);
    const days = period === "7d" ? 7 : period === "30d" ? 30 : period === "90d" ? 90 : 365;
    const to = new Date(now.getTime() + days * 86400000).toISOString().slice(0, 10);
    return { date_from: from, date_to: to };
  }, [period]);

  const { data, isLoading, refetch } = useQuery<EventsResponse>({
    queryKey: ["map", "artist-events", eventType, city, artistSearch, scoreMin, period],
    queryFn: () =>
      eventsMapApi.getEvents({
        event_type: eventType !== "all" ? eventType : undefined,
        city: city !== "all" ? city : undefined,
        artist: artistSearch || undefined,
        score_min: scoreMin > 0 ? scoreMin : undefined,
        ...periodDates,
      }),
  });

  const toggleType = useCallback((type: string) => {
    setActiveTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        if (next.size > 1) next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  }, []);

  const filteredEvents = useMemo(() => {
    if (!data?.events) return [];
    return data.events.filter((e) => activeTypes.has(e.event_type));
  }, [data?.events, activeTypes]);

  const hasFilters =
    eventType !== "all" || city !== "all" || artistSearch.length > 0 || scoreMin > 0 || period !== "all";

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Carte des Événements</h1>
          <p className="text-sm text-muted-foreground">
            Concerts, festivals, pop-up stores et événements de marque en
            France
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {data?.stats && (
            <>
              <div className="flex items-center gap-1.5 px-2.5 py-1 bg-indigo-50 rounded-md">
                <Music className="h-3.5 w-3.5 text-indigo-600" />
                <span className="text-xs font-medium text-indigo-700">
                  {data.total} événements
                </span>
              </div>
              <div className="flex items-center gap-1.5 px-2.5 py-1 bg-purple-50 rounded-md">
                <Users className="h-3.5 w-3.5 text-purple-600" />
                <span className="text-xs font-medium text-purple-700">
                  {data.stats.total_artists} artistes
                </span>
              </div>
              {data.source === "ticketmaster" && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 bg-green-50 rounded-md">
                  <span className="text-[10px] font-medium text-green-700">✅ Données réelles</span>
                </div>
              )}
              {data.source === "generated" && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 bg-amber-50 rounded-md">
                  <span className="text-[10px] font-medium text-amber-700">⚡ Estimations</span>
                </div>
              )}
            </>
          )}
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs gap-1"
            onClick={async () => {
              try {
                await eventsMapApi.syncEvents();
                setTimeout(() => refetch(), 3000);
              } catch {}
            }}
          >
            <RefreshCw className="h-3 w-3" />
            Sync
          </Button>
        </div>
      </div>

      {/* Filters bar */}
      <div className="flex flex-wrap items-center gap-3 p-3 bg-muted/40 rounded-lg border">
        <div className="flex items-center gap-1.5">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs font-medium text-muted-foreground">
            Filtres
          </span>
        </div>

        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Rechercher un artiste..."
            className="h-8 w-48 pl-8 text-xs"
            value={artistSearch}
            onChange={(e) => setArtistSearch(e.target.value)}
          />
        </div>

        <Select value={city} onValueChange={setCity}>
          <SelectTrigger className="h-8 w-[140px] text-xs">
            <SelectValue placeholder="Ville" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Toutes les villes</SelectItem>
            {data?.cities?.map((c) => (
              <SelectItem key={c} value={c}>
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={String(scoreMin)} onValueChange={(v) => setScoreMin(Number(v))}>
          <SelectTrigger className="h-8 w-[130px] text-xs">
            <SelectValue placeholder="Score min" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="0">Tous les scores</SelectItem>
            <SelectItem value="30">Score ≥ 30</SelectItem>
            <SelectItem value="50">Score ≥ 50</SelectItem>
            <SelectItem value="70">Score ≥ 70</SelectItem>
          </SelectContent>
        </Select>

        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="h-8 w-[120px] text-xs">
            <SelectValue placeholder="Période" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Toute période</SelectItem>
            <SelectItem value="7d">7 prochains jours</SelectItem>
            <SelectItem value="30d">30 prochains jours</SelectItem>
            <SelectItem value="90d">3 prochains mois</SelectItem>
          </SelectContent>
        </Select>

        {hasFilters && (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-xs"
            onClick={() => {
              setEventType("all");
              setCity("all");
              setArtistSearch("");
              setScoreMin(0);
              setPeriod("all");
            }}
          >
            <X className="h-3 w-3 mr-1" />
            Réinitialiser
          </Button>
        )}
      </div>

      {/* Type toggles */}
      <div className="flex items-center gap-2 flex-wrap">
        {Object.entries(EVENT_TYPES).map(([key, config]) => {
          const Icon = config.icon;
          const isActive = activeTypes.has(key);
          const count = data?.stats?.by_type?.[key] || 0;
          return (
            <button
              key={key}
              onClick={() => toggleType(key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all border ${
                isActive
                  ? `${config.lightBg} ${config.textColor} ${config.borderColor}`
                  : "bg-muted/50 text-muted-foreground border-transparent opacity-50"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {config.label}
              <span
                className={`ml-0.5 px-1.5 py-0 rounded-full text-[10px] ${
                  isActive ? config.bgColor + " text-white" : "bg-muted"
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Main content: Map + sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Map */}
        <div className="lg:col-span-2">
          {isLoading ? (
            <div className="h-[600px] bg-muted rounded-xl flex items-center justify-center">
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                <span className="text-sm text-muted-foreground">
                  Chargement...
                </span>
              </div>
            </div>
          ) : (
            <MapView
              events={filteredEvents}
              selectedEvent={selectedEvent}
              onSelectEvent={setSelectedEvent}
              eventTypes={EVENT_TYPES}
            />
          )}
        </div>

        {/* Sidebar: event list */}
        <div className="lg:col-span-1">
          {/* Selected event detail */}
          {selectedEvent && (
            <Card className="mb-4 border-2" style={{
              borderColor: EVENT_TYPES[selectedEvent.event_type]?.color || "#6366f1",
            }}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <Badge
                    className="text-xs"
                    style={{
                      backgroundColor:
                        EVENT_TYPES[selectedEvent.event_type]?.color,
                      color: "white",
                    }}
                  >
                    {selectedEvent.event_type_label}
                  </Badge>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => setSelectedEvent(null)}
                  >
                    <X className="h-3.5 w-3.5" />
                  </Button>
                </div>
                <div className="flex items-center gap-3 mb-3">
                  {selectedEvent.artist_image ? (
                    <img
                      src={selectedEvent.artist_image}
                      alt={selectedEvent.artist_name}
                      className="w-14 h-14 rounded-full object-cover"
                    />
                  ) : (
                    <div className="w-14 h-14 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                      <Music className="h-6 w-6 text-white" />
                    </div>
                  )}
                  <div>
                    <h3 className="font-bold text-lg">
                      {selectedEvent.artist_name}
                    </h3>
                    {selectedEvent.artist_genres.length > 0 && (
                      <div className="flex gap-1 mt-0.5">
                        {selectedEvent.artist_genres.map((g) => (
                          <Badge
                            key={g}
                            variant="outline"
                            className="text-[10px] px-1.5 py-0"
                          >
                            {g}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                    <span>
                      {selectedEvent.venue}, {selectedEvent.city}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span>{selectedEvent.date_label}</span>
                  </div>
                  {selectedEvent.capacity && (
                    <div className="flex items-center gap-2">
                      <Users className="h-4 w-4 text-muted-foreground" />
                      <span>
                        {selectedEvent.capacity.toLocaleString()} places
                      </span>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground text-xs">Prix</span>
                    <span className="font-medium">
                      {selectedEvent.price_min}€ – {selectedEvent.price_max}€
                    </span>
                  </div>
                  {selectedEvent.monthly_listeners > 0 && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground text-xs">
                        Auditeurs Spotify
                      </span>
                      <span className="font-medium">
                        {formatListeners(selectedEvent.monthly_listeners)}
                      </span>
                    </div>
                  )}
                  {selectedEvent.fee_estimate_min && selectedEvent.fee_estimate_max && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground text-xs">Cachet estimé</span>
                      <span className="font-medium">
                        {Math.round(selectedEvent.fee_estimate_min / 1000)}–{Math.round(selectedEvent.fee_estimate_max / 1000)}k€
                      </span>
                    </div>
                  )}
                  {selectedEvent.has_contact !== undefined && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground text-xs">Contact</span>
                      <span className={`text-xs font-medium ${selectedEvent.has_contact ? "text-green-600" : "text-orange-500"}`}>
                        {selectedEvent.has_contact ? "✓ Trouvé" : "✗ Manquant"}
                      </span>
                    </div>
                  )}
                </div>
                <div className="mt-3 pt-3 border-t flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        selectedEvent.artist_score >= 70
                          ? "bg-green-500"
                          : selectedEvent.artist_score >= 40
                          ? "bg-yellow-500"
                          : "bg-red-500"
                      }`}
                    />
                    <span className="text-xs text-muted-foreground">
                      Score: {selectedEvent.artist_score}
                    </span>
                  </div>
                  <Button variant="outline" size="sm" className="text-xs h-7" asChild>
                    <a href={`/discovery?search=${encodeURIComponent(selectedEvent.artist_name)}`}>
                      <Eye className="h-3 w-3 mr-1" />
                      Voir l&apos;artiste
                    </a>
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Event list */}
          <Card>
            <CardHeader className="pb-2 px-4 pt-4">
              <CardTitle className="text-sm font-medium flex items-center justify-between">
                <span>Événements à venir</span>
                <Badge variant="secondary" className="text-[10px]">
                  {filteredEvents.length}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="px-3 pb-3">
              <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
                {filteredEvents.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <MapPin className="h-8 w-8 mx-auto mb-2 opacity-30" />
                    <p className="text-sm">Aucun événement trouvé</p>
                    <p className="text-xs mt-1">
                      Ajoutez des artistes dans Discovery
                    </p>
                  </div>
                ) : (
                  filteredEvents.slice(0, 50).map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      onSelect={setSelectedEvent}
                      isSelected={selectedEvent?.id === event.id}
                    />
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* City stats */}
      {data?.stats?.by_city &&
        Object.keys(data.stats.by_city).length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-6 gap-2">
            {Object.entries(data.stats.by_city)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 12)
              .map(([cityName, count]) => (
                <button
                  key={cityName}
                  onClick={() =>
                    setCity(city === cityName ? "all" : cityName)
                  }
                  className={`p-2.5 rounded-lg border text-center transition-all hover:shadow-sm ${
                    city === cityName
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-card hover:bg-muted/50"
                  }`}
                >
                  <p className="font-bold text-lg">{count}</p>
                  <p className="text-[11px] truncate">{cityName}</p>
                </button>
              ))}
          </div>
        )}
    </div>
  );
}

export default function MapPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <MapContent />
      </AppLayout>
    </ProtectedRoute>
  );
}