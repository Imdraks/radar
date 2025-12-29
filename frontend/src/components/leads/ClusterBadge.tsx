"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  Copy,
  Link2,
  Hash,
  FileText,
  Brain,
  ChevronDown,
  ExternalLink,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { clustersApi } from "@/lib/api";
import type { OpportunityCluster, ClusterMatchType } from "@/lib/types";
import { truncate } from "@/lib/utils";

interface ClusterBadgeProps {
  leadId: number;
  showDetails?: boolean;
}

function getMatchTypeInfo(matchType: ClusterMatchType) {
  switch (matchType) {
    case "url":
      return {
        icon: <Link2 className="h-3 w-3" />,
        label: "URL identique",
        color: "bg-blue-100 text-blue-700 border-blue-200",
      };
    case "hash":
      return {
        icon: <Hash className="h-3 w-3" />,
        label: "Contenu similaire",
        color: "bg-purple-100 text-purple-700 border-purple-200",
      };
    case "text":
      return {
        icon: <FileText className="h-3 w-3" />,
        label: "Titre similaire",
        color: "bg-orange-100 text-orange-700 border-orange-200",
      };
    case "ai":
      return {
        icon: <Brain className="h-3 w-3" />,
        label: "IA",
        color: "bg-green-100 text-green-700 border-green-200",
      };
    default:
      return {
        icon: <Copy className="h-3 w-3" />,
        label: "Doublon",
        color: "bg-gray-100 text-gray-700 border-gray-200",
      };
  }
}

export function ClusterBadge({ leadId, showDetails = true }: ClusterBadgeProps) {
  const { data: cluster, isLoading } = useQuery<OpportunityCluster | null>({
    queryKey: ["clusters", "lead", leadId],
    queryFn: () => clustersApi.getForOpportunity(leadId).catch(() => null),
    staleTime: 60000, // Cache for 1 minute
  });

  // Don't show anything if not in a cluster or is canonical
  if (isLoading || !cluster) {
    return null;
  }

  const isCanonical = cluster.canonical_id === leadId;
  const matchInfo = getMatchTypeInfo(cluster.match_type);
  const duplicateCount = cluster.members.length - 1;

  // Simple badge for canonical/single view
  if (!showDetails) {
    if (isCanonical && duplicateCount > 0) {
      return (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              <Badge variant="outline" className="gap-1 cursor-help">
                <Copy className="h-3 w-3" />
                {duplicateCount} doublon{duplicateCount > 1 ? "s" : ""}
              </Badge>
            </TooltipTrigger>
            <TooltipContent>
              <p>Ce lead a {duplicateCount} doublon{duplicateCount > 1 ? "s" : ""}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );
    }

    if (!isCanonical) {
      return (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              <Badge variant="outline" className={`gap-1 cursor-help ${matchInfo.color}`}>
                {matchInfo.icon}
                Doublon
              </Badge>
            </TooltipTrigger>
            <TooltipContent>
              <p>Doublon détecté par {matchInfo.label.toLowerCase()}</p>
              <Link href={`/leads/${cluster.canonical_id}`} className="text-primary underline">
                Voir l&apos;original
              </Link>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );
    }

    return null;
  }

  // Detailed popover for main view
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className={`gap-1 ${isCanonical ? "" : matchInfo.color}`}>
          <Copy className="h-3 w-3" />
          {isCanonical ? (
            <>{duplicateCount} doublon{duplicateCount > 1 ? "s" : ""}</>
          ) : (
            <>Doublon</>
          )}
          <ChevronDown className="h-3 w-3 ml-1" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80" align="start">
        <div className="space-y-3">
          {/* Header */}
          <div className="flex items-center justify-between">
            <h4 className="font-semibold">Cluster de doublons</h4>
            <Badge variant="outline" className={matchInfo.color}>
              {matchInfo.icon}
              <span className="ml-1">{matchInfo.label}</span>
            </Badge>
          </div>

          {/* Confidence */}
          <div className="text-sm text-muted-foreground">
            Confiance: {Math.round(cluster.confidence * 100)}%
          </div>

          {/* Status */}
          {isCanonical ? (
            <div className="p-2 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm">
              ✅ Ceci est le lead principal du cluster
            </div>
          ) : (
            <div className="p-2 rounded-lg bg-yellow-50 border border-yellow-200 text-yellow-700 text-sm">
              ⚠️ Ceci est un doublon. Le lead principal est plus complet.
            </div>
          )}

          {/* Members list */}
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">
              Leads liés ({cluster.members.length})
            </p>
            <div className="max-h-40 overflow-y-auto space-y-1">
              {cluster.members.map((member) => (
                <Link
                  key={member.opportunity_id}
                  href={`/leads/${member.opportunity_id}`}
                  className={`flex items-center justify-between p-2 rounded-lg text-sm hover:bg-muted transition-colors ${
                    member.opportunity_id === leadId ? "bg-muted" : ""
                  }`}
                >
                  <span className="flex items-center gap-2 truncate">
                    {member.is_canonical && (
                      <Badge variant="default" className="text-xs px-1">
                        ★
                      </Badge>
                    )}
                    <span className="truncate">
                      {member.opportunity?.title
                        ? truncate(member.opportunity.title, 30)
                        : `#${member.opportunity_id}`}
                    </span>
                  </span>
                  {member.opportunity_id !== leadId && (
                    <ExternalLink className="h-3 w-3 text-muted-foreground" />
                  )}
                </Link>
              ))}
            </div>
          </div>

          {/* Action for duplicates */}
          {!isCanonical && (
            <Link href={`/leads/${cluster.canonical_id}`}>
              <Button size="sm" className="w-full">
                Voir le lead principal
              </Button>
            </Link>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}

export default ClusterBadge;
