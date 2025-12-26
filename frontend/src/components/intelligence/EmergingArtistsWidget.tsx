"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { 
  Sparkles, 
  TrendingUp, 
  Wallet, 
  Music,
  ExternalLink,
  Star,
  Loader2,
  CheckCircle,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

interface ArtistSuggestion {
  name: string;
  real_name?: string;
  genre: string;
  spotify_monthly_listeners: number;
  youtube_subscribers: number;
  instagram_followers: number;
  tiktok_followers: number;
  fee_min: number;
  fee_max: number;
  market_tier: string;
  record_label?: string;
  potential_reason: string;
}

interface SuggestionsResponse {
  emerging: ArtistSuggestion[];
  rising: ArtistSuggestion[];
  budget_friendly: ArtistSuggestion[];
}

function formatNumber(num: number) {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(0)}K`;
  return num.toString();
}

// Calculer un score de potentiel (1-100) basé sur les critères
function calculatePotentialScore(artist: ArtistSuggestion): number {
  let score = 0;
  
  // Score basé sur le tier (0-30 points)
  const tierScores: Record<string, number> = {
    emerging: 25,
    developing: 20,
    established: 15,
    star: 10, // Moins intéressant pour découverte
  };
  score += tierScores[artist.market_tier] || 15;
  
  // Score basé sur le ratio audience/prix (0-40 points)
  const avgFee = (artist.fee_min + artist.fee_max) / 2;
  const totalAudience = 
    (artist.spotify_monthly_listeners || 0) + 
    (artist.youtube_subscribers || 0) * 2 + 
    (artist.instagram_followers || 0) + 
    (artist.tiktok_followers || 0);
  
  if (avgFee > 0 && totalAudience > 0) {
    const ratio = totalAudience / avgFee;
    if (ratio > 500) score += 40;
    else if (ratio > 200) score += 35;
    else if (ratio > 100) score += 30;
    else if (ratio > 50) score += 25;
    else if (ratio > 20) score += 20;
    else score += 15;
  } else {
    score += 20;
  }
  
  // Score basé sur le prix abordable (0-30 points)
  if (artist.fee_max < 8000) score += 30;
  else if (artist.fee_max < 15000) score += 25;
  else if (artist.fee_max < 25000) score += 20;
  else if (artist.fee_max < 40000) score += 15;
  else score += 10;
  
  return Math.min(100, Math.max(1, Math.round(score)));
}

function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-600 bg-green-100 dark:bg-green-900/30";
  if (score >= 60) return "text-blue-600 bg-blue-100 dark:bg-blue-900/30";
  if (score >= 40) return "text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30";
  return "text-orange-600 bg-orange-100 dark:bg-orange-900/30";
}

function getTierColor(tier: string) {
  const colors: Record<string, string> = {
    emerging: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    developing: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200",
    established: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    star: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  };
  return colors[tier] || "bg-gray-100 text-gray-800";
}

function getTierLabel(tier: string) {
  const labels: Record<string, string> = {
    emerging: "Émergent",
    developing: "En développement",
    established: "Établi",
    star: "Star",
  };
  return labels[tier] || tier;
}

function ArtistCard({ artist, type, onAnalyze }: { 
  artist: ArtistSuggestion; 
  type: "emerging" | "rising" | "budget";
  onAnalyze: (artistName: string) => void;
}) {
  const typeConfig = {
    emerging: { icon: Sparkles, color: "text-purple-500", bg: "bg-purple-50 dark:bg-purple-900/20" },
    rising: { icon: TrendingUp, color: "text-green-500", bg: "bg-green-50 dark:bg-green-900/20" },
    budget: { icon: Wallet, color: "text-blue-500", bg: "bg-blue-50 dark:bg-blue-900/20" },
  };
  
  const config = typeConfig[type];
  const Icon = config.icon;
  const potentialScore = calculatePotentialScore(artist);

  const handleAnalyze = () => {
    onAnalyze(artist.name);
  };

  return (
    <div className={`flex-shrink-0 w-[280px] p-4 rounded-lg border ${config.bg}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon className={`h-4 w-4 ${config.color}`} />
          <span className="font-semibold text-sm truncate max-w-[150px]">{artist.name}</span>
        </div>
        <Badge variant="outline" className="text-xs">
          {artist.genre}
        </Badge>
      </div>
      
      <div className="flex items-center gap-2 mb-3">
        <Badge className={`text-xs ${getTierColor(artist.market_tier)}`}>
          {getTierLabel(artist.market_tier)}
        </Badge>
        <div className={`flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded ${getScoreColor(potentialScore)}`}>
          <Star className="h-3 w-3" />
          {potentialScore}/100
        </div>
      </div>
      
      <div className="mb-3">
        <div className="text-lg font-bold text-green-600 dark:text-green-400">
          {artist.fee_min.toLocaleString()}€ - {artist.fee_max.toLocaleString()}€
        </div>
      </div>
      
      <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
        {artist.potential_reason}
      </p>
      
      <div className="flex gap-2">
        <Button 
          variant="default" 
          size="sm" 
          className="flex-1 text-xs"
          onClick={handleAnalyze}
        >
          <Music className="h-3 w-3 mr-1" />
          Voir profil
        </Button>
        <Button 
          variant="ghost" 
          size="sm" 
          className="px-2"
          onClick={() => window.open(`https://open.spotify.com/search/${encodeURIComponent(artist.name)}`, "_blank")}
        >
          <ExternalLink className="h-3 w-3" />
        </Button>
      </div>
    </div>
  );
}

function ArtistCardSkeleton() {
  return (
    <div className="flex-shrink-0 w-[280px] p-4 rounded-lg border bg-gray-50 dark:bg-gray-900/20">
      <div className="flex items-start justify-between mb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-5 w-12" />
      </div>
      <div className="flex items-center gap-2 mb-3">
        <Skeleton className="h-5 w-20" />
        <Skeleton className="h-4 w-12" />
      </div>
      <Skeleton className="h-6 w-32 mb-3" />
      <Skeleton className="h-8 w-full mb-3" />
      <Skeleton className="h-8 w-full" />
    </div>
  );
}

export function EmergingArtistsWidget() {
  const router = useRouter();
  const [analyzingArtist, setAnalyzingArtist] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState<"loading" | "success" | "error">("loading");
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const { data: suggestions, isLoading } = useQuery<SuggestionsResponse>({
    queryKey: ["artist-suggestions"],
    queryFn: async () => {
      const response = await api.get("/artist-history/suggestions/all?limit=8");
      return response.data;
    },
    staleTime: 1000 * 60 * 5, // Cache 5 minutes
  });

  // Mutation pour lancer l'analyse
  const analyzeMutation = useMutation({
    mutationFn: async (artistName: string) => {
      const response = await api.post("/ingestion/analyze-artist", {
        artist_name: artistName,
        force_refresh: true,
      });
      return response.data;
    },
    onSuccess: (data) => {
      setTaskId(data.task_id);
    },
    onError: (error: any) => {
      setAnalysisStatus("error");
      setAnalysisError(error?.response?.data?.detail || "Erreur lors du lancement de l'analyse");
    },
  });

  // Polling pour vérifier le statut de la tâche
  const { data: taskStatus } = useQuery({
    queryKey: ["artist-task", taskId],
    queryFn: async () => {
      const response = await api.get(`/ingestion/task/${taskId}`);
      return response.data;
    },
    enabled: !!taskId && analysisStatus === "loading",
    refetchInterval: 2000,
  });

  // Gérer les changements de statut de la tâche
  useEffect(() => {
    if (taskStatus) {
      // Simuler une progression
      if (!taskStatus.ready) {
        setAnalysisProgress((prev) => Math.min(prev + 15, 85));
      }

      if (taskStatus.ready) {
        if (taskStatus.result) {
          setAnalysisStatus("success");
          setAnalysisProgress(100);
          // Rediriger vers la page artist-history après 1.5s
          setTimeout(() => {
            setDialogOpen(false);
            router.push(`/artist-history?search=${encodeURIComponent(analyzingArtist || "")}`);
            resetAnalysis();
          }, 1500);
        } else if (taskStatus.error) {
          setAnalysisStatus("error");
          setAnalysisError(taskStatus.error);
        }
      }
    }
  }, [taskStatus, analyzingArtist, router]);

  const handleAnalyze = (artistName: string) => {
    setAnalyzingArtist(artistName);
    setDialogOpen(true);
    setAnalysisStatus("loading");
    setAnalysisProgress(10);
    setAnalysisError(null);
    setTaskId(null);
    analyzeMutation.mutate(artistName);
  };

  const resetAnalysis = () => {
    setAnalyzingArtist(null);
    setTaskId(null);
    setAnalysisStatus("loading");
    setAnalysisProgress(0);
    setAnalysisError(null);
  };

  const handleDialogClose = (open: boolean) => {
    if (!open) {
      setDialogOpen(false);
      resetAnalysis();
    }
  };

  return (
    <>
      {/* Dialog d'analyse en cours */}
      <Dialog open={dialogOpen} onOpenChange={handleDialogClose}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {analysisStatus === "loading" && <Loader2 className="h-5 w-5 animate-spin text-blue-500" />}
              {analysisStatus === "success" && <CheckCircle className="h-5 w-5 text-green-500" />}
              {analysisStatus === "error" && <XCircle className="h-5 w-5 text-red-500" />}
              Analyse de {analyzingArtist}
            </DialogTitle>
            <DialogDescription>
              {analysisStatus === "loading" && "Collecte des données en cours..."}
              {analysisStatus === "success" && "Analyse terminée ! Redirection..."}
              {analysisStatus === "error" && "Une erreur est survenue"}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {analysisStatus === "loading" && (
              <>
                <Progress value={analysisProgress} className="h-2" />
                <div className="space-y-2 text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Recherche sur Spotify, YouTube, Instagram...
                  </div>
                  {analysisProgress > 30 && (
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-3 w-3 text-green-500" />
                      Données sociales récupérées
                    </div>
                  )}
                  {analysisProgress > 60 && (
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      Analyse IA des cachets...
                    </div>
                  )}
                </div>
              </>
            )}
            
            {analysisStatus === "success" && (
              <div className="text-center py-4">
                <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-2" />
                <p className="font-medium">Profil de {analyzingArtist} prêt !</p>
                <p className="text-sm text-muted-foreground">Redirection en cours...</p>
              </div>
            )}
            
            {analysisStatus === "error" && (
              <div className="text-center py-4">
                <XCircle className="h-12 w-12 text-red-500 mx-auto mb-2" />
                <p className="font-medium text-red-600">Erreur d'analyse</p>
                <p className="text-sm text-muted-foreground">{analysisError}</p>
                <Button 
                  className="mt-4" 
                  onClick={() => analyzingArtist && handleAnalyze(analyzingArtist)}
                >
                  Réessayer
                </Button>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Star className="h-5 w-5 text-yellow-500" />
              Artistes Suggérés
            </CardTitle>
            <CardDescription>
              Découvrez les talents émergents avec le meilleur potentiel
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link href="/artist-history">
              <Music className="h-4 w-4 mr-2" />
              Tous les artistes
            </Link>
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="emerging" className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-4">
            <TabsTrigger value="emerging" className="gap-1">
              <Sparkles className="h-3 w-3" />
              <span className="hidden sm:inline">Émergents</span>
            </TabsTrigger>
            <TabsTrigger value="rising" className="gap-1">
              <TrendingUp className="h-3 w-3" />
              <span className="hidden sm:inline">En hausse</span>
            </TabsTrigger>
            <TabsTrigger value="budget" className="gap-1">
              <Wallet className="h-3 w-3" />
              <span className="hidden sm:inline">Petit budget</span>
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="emerging" className="mt-0">
            <ScrollArea className="w-full whitespace-nowrap">
              <div className="flex gap-4 pb-4">
                {isLoading ? (
                  Array.from({ length: 4 }).map((_, i) => <ArtistCardSkeleton key={i} />)
                ) : suggestions?.emerging.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground w-full">
                    Aucune suggestion disponible
                  </div>
                ) : (
                  suggestions?.emerging.map((artist, i) => (
                    <ArtistCard 
                      key={i} 
                      artist={artist} 
                      type="emerging"
                      onAnalyze={handleAnalyze}
                    />
                  ))
                )}
              </div>
              <ScrollBar orientation="horizontal" />
            </ScrollArea>
            <p className="text-xs text-muted-foreground mt-2">
              💡 Artistes émergents avec fort potentiel et cachets abordables
            </p>
          </TabsContent>
          
          <TabsContent value="rising" className="mt-0">
            <ScrollArea className="w-full whitespace-nowrap">
              <div className="flex gap-4 pb-4">
                {isLoading ? (
                  Array.from({ length: 4 }).map((_, i) => <ArtistCardSkeleton key={i} />)
                ) : suggestions?.rising.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground w-full">
                    Aucune suggestion disponible
                  </div>
                ) : (
                  suggestions?.rising.map((artist, i) => (
                    <ArtistCard 
                      key={i} 
                      artist={artist} 
                      type="rising"
                      onAnalyze={handleAnalyze}
                    />
                  ))
                )}
              </div>
              <ScrollBar orientation="horizontal" />
            </ScrollArea>
            <p className="text-xs text-muted-foreground mt-2">
              🚀 Artistes en forte progression, proches de devenir établis
            </p>
          </TabsContent>
          
          <TabsContent value="budget" className="mt-0">
            <ScrollArea className="w-full whitespace-nowrap">
              <div className="flex gap-4 pb-4">
                {isLoading ? (
                  Array.from({ length: 4 }).map((_, i) => <ArtistCardSkeleton key={i} />)
                ) : suggestions?.budget_friendly.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground w-full">
                    Aucune suggestion disponible
                  </div>
                ) : (
                  suggestions?.budget_friendly.map((artist, i) => (
                    <ArtistCard 
                      key={i} 
                      artist={artist} 
                      type="budget"
                      onAnalyze={handleAnalyze}
                    />
                  ))
                )}
              </div>
              <ScrollBar orientation="horizontal" />
            </ScrollArea>
            <p className="text-xs text-muted-foreground mt-2">
              💰 Meilleur rapport qualité/prix pour les budgets serrés (&lt; 15 000€)
            </p>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
    </>
  );
}
