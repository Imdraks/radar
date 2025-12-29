"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Target,
  Star,
  TrendingUp,
  ChevronDown,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { profilesApi } from "@/lib/api";
import type { OpportunityProfileScore, Profile } from "@/lib/types";

interface FitScoreBadgeProps {
  opportunityId: number;
  profileId?: number;
  score?: number; // Optional pre-computed score
  showDetails?: boolean;
}

function getScoreColor(score: number): string {
  if (score >= 85) return "text-green-600";
  if (score >= 70) return "text-yellow-600";
  if (score >= 50) return "text-orange-600";
  return "text-red-600";
}

function getScoreBgColor(score: number): string {
  if (score >= 85) return "bg-green-100 border-green-200";
  if (score >= 70) return "bg-yellow-100 border-yellow-200";
  if (score >= 50) return "bg-orange-100 border-orange-200";
  return "bg-red-100 border-red-200";
}

function getScoreLabel(score: number): string {
  if (score >= 85) return "Excellent";
  if (score >= 70) return "Bon";
  if (score >= 50) return "Moyen";
  return "Faible";
}

function getScoreEmoji(score: number): string {
  if (score >= 85) return "🌟";
  if (score >= 70) return "✅";
  if (score >= 50) return "📊";
  return "⚠️";
}

export function FitScoreBadge({ 
  opportunityId, 
  profileId,
  score: precomputedScore,
  showDetails = true 
}: FitScoreBadgeProps) {
  // Fetch profiles if we need to show detailed breakdown
  const { data: profiles } = useQuery<Profile[]>({
    queryKey: ["profiles"],
    queryFn: profilesApi.getAll,
    enabled: showDetails && !precomputedScore,
  });

  // Fetch scores for this opportunity across profiles
  const { data: scores, isLoading } = useQuery<OpportunityProfileScore[]>({
    queryKey: ["opportunity-scores", opportunityId],
    queryFn: async () => {
      if (!profiles || profiles.length === 0) return [];
      // Fetch scores from all profiles
      const allScores: OpportunityProfileScore[] = [];
      for (const profile of profiles) {
        try {
          const profileScores = await profilesApi.getScores(profile.id, 100);
          const matchingScore = profileScores.find(
            (s: OpportunityProfileScore) => s.opportunity_id === opportunityId
          );
          if (matchingScore) {
            allScores.push({ ...matchingScore, profile_id: profile.id });
          }
        } catch (e) {
          // Skip if profile scores not available
        }
      }
      return allScores;
    },
    enabled: showDetails && !!profiles && profiles.length > 0 && !precomputedScore,
    staleTime: 60000,
  });

  // Use precomputed score or best score from profiles
  const displayScore = precomputedScore ?? (scores && scores.length > 0 
    ? Math.max(...scores.map(s => s.fit_score)) 
    : null);

  if (isLoading && !precomputedScore) {
    return null;
  }

  if (displayScore === null || displayScore === undefined) {
    return null;
  }

  // Simple badge view
  if (!showDetails) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger>
            <Badge 
              variant="outline" 
              className={`gap-1 cursor-help ${getScoreBgColor(displayScore)}`}
            >
              <Target className="h-3 w-3" />
              <span className={getScoreColor(displayScore)}>
                {displayScore.toFixed(0)}%
              </span>
            </Badge>
          </TooltipTrigger>
          <TooltipContent>
            <p>Fit Score: {getScoreLabel(displayScore)}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  // Detailed popover view
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button 
          variant="outline" 
          size="sm" 
          className={`gap-1 ${getScoreBgColor(displayScore)}`}
        >
          <Target className="h-3 w-3" />
          <span className={getScoreColor(displayScore)}>
            {displayScore.toFixed(0)}% Fit
          </span>
          <ChevronDown className="h-3 w-3 ml-1" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-72" align="start">
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <h4 className="font-semibold">Fit Score</h4>
            <Badge className={getScoreBgColor(displayScore)}>
              {getScoreEmoji(displayScore)} {getScoreLabel(displayScore)}
            </Badge>
          </div>

          {/* Main score */}
          <div className="text-center py-3">
            <div className={`text-4xl font-bold ${getScoreColor(displayScore)}`}>
              {displayScore.toFixed(0)}%
            </div>
            <Progress 
              value={displayScore} 
              className="h-2 mt-2"
            />
          </div>

          {/* Scores by profile */}
          {scores && scores.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">
                Par profil
              </p>
              {scores.map((score) => {
                const profile = profiles?.find(p => p.id === score.profile_id);
                return (
                  <div 
                    key={score.profile_id} 
                    className="flex items-center justify-between p-2 rounded-lg bg-muted/50"
                  >
                    <span className="text-sm truncate">
                      {profile?.name || `Profil #${score.profile_id}`}
                    </span>
                    <div className="flex items-center gap-2">
                      <Progress 
                        value={score.fit_score} 
                        className="h-1.5 w-12"
                      />
                      <span className={`text-sm font-medium ${getScoreColor(score.fit_score)}`}>
                        {score.fit_score.toFixed(0)}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Explanation */}
          <div className="pt-2 border-t text-xs text-muted-foreground">
            <p>
              Le Fit Score mesure l&apos;adéquation de cette opportunité avec vos 
              critères de profil (budget, deadline, catégorie, etc.)
            </p>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}

export default FitScoreBadge;
