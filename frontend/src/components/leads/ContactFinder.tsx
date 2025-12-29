"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Search,
  Mail,
  Phone,
  Globe,
  Linkedin,
  Twitter,
  Loader2,
  CheckCircle,
  ExternalLink,
  AlertCircle,
  Info,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { useToast } from "@/components/ui/toaster";
import { contactFinderApi } from "@/lib/api";
import type { ContactFinderResult, ContactInfo } from "@/lib/types";

interface ContactFinderProps {
  opportunityId: number;
}

function getContactIcon(type: ContactInfo["type"]) {
  switch (type) {
    case "email":
      return <Mail className="h-4 w-4" />;
    case "phone":
      return <Phone className="h-4 w-4" />;
    case "website":
      return <Globe className="h-4 w-4" />;
    case "linkedin":
      return <Linkedin className="h-4 w-4" />;
    case "twitter":
      return <Twitter className="h-4 w-4" />;
    default:
      return null;
  }
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.9) return "text-green-500";
  if (confidence >= 0.7) return "text-yellow-500";
  return "text-orange-500";
}

function ContactItem({ contact }: { contact: ContactInfo }) {
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-full bg-muted">
          {getContactIcon(contact.type)}
        </div>
        <div>
          <div className="font-medium">{contact.value}</div>
          <div className="text-xs text-muted-foreground flex items-center gap-2">
            <span className="capitalize">{contact.type}</span>
            <span>•</span>
            <span className={getConfidenceColor(contact.confidence)}>
              {Math.round(contact.confidence * 100)}% confiance
            </span>
            <span>•</span>
            <span>via {contact.source}</span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => copyToClipboard(contact.value)}
              >
                Copier
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Copier dans le presse-papier</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
        {contact.type === "email" && (
          <Button size="sm" variant="outline" asChild>
            <a href={`mailto:${contact.value}`}>
              <Mail className="h-4 w-4 mr-1" />
              Envoyer
            </a>
          </Button>
        )}
        {contact.type === "phone" && (
          <Button size="sm" variant="outline" asChild>
            <a href={`tel:${contact.value}`}>
              <Phone className="h-4 w-4 mr-1" />
              Appeler
            </a>
          </Button>
        )}
        {(contact.type === "website" || contact.type === "linkedin" || contact.type === "twitter") && (
          <Button size="sm" variant="outline" asChild>
            <a href={contact.value} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-4 w-4 mr-1" />
              Ouvrir
            </a>
          </Button>
        )}
      </div>
    </div>
  );
}

export function ContactFinder({ opportunityId }: ContactFinderProps) {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const [showEvidence, setShowEvidence] = useState(false);
  const [options, setOptions] = useState({
    search_web: true,
    search_linkedin: false,
    max_results: 5,
  });

  // Fetch existing result
  const { data: existingResult, isLoading: resultLoading } = useQuery<ContactFinderResult | null>({
    queryKey: ["contact-finder", opportunityId],
    queryFn: () => contactFinderApi.getResult(opportunityId).catch(() => null),
  });

  // Find contacts mutation
  const findMutation = useMutation({
    mutationFn: () => contactFinderApi.find(opportunityId, options),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["contact-finder", opportunityId] });
      if (data.contacts && data.contacts.length > 0) {
        addToast({
          title: "Contacts trouvés",
          description: `${data.contacts.length} contact(s) trouvé(s)`,
          type: "success",
        });
      } else {
        addToast({
          title: "Aucun contact trouvé",
          description: "La recherche n'a pas retourné de résultats",
          type: "warning",
        });
      }
    },
    onError: () => {
      addToast({
        title: "Erreur",
        description: "Impossible de lancer la recherche",
        type: "error",
      });
    },
  });

  const isSearching = findMutation.isPending || existingResult?.status === "searching";
  const hasResults = existingResult?.contacts && existingResult.contacts.length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="h-5 w-5" />
          Contact Finder
        </CardTitle>
        <CardDescription>
          Trouvez les coordonnées de contact pour cette opportunité
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Search options */}
        {!hasResults && (
          <div className="space-y-4 p-4 rounded-lg border bg-muted/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4" />
                <Label htmlFor="search-web">Recherche web</Label>
              </div>
              <Switch
                id="search-web"
                checked={options.search_web}
                onCheckedChange={(checked) =>
                  setOptions((prev) => ({ ...prev, search_web: checked }))
                }
              />
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Linkedin className="h-4 w-4" />
                <Label htmlFor="search-linkedin">LinkedIn</Label>
                <Badge variant="secondary" className="text-xs">
                  Premium
                </Badge>
              </div>
              <Switch
                id="search-linkedin"
                checked={options.search_linkedin}
                onCheckedChange={(checked) =>
                  setOptions((prev) => ({ ...prev, search_linkedin: checked }))
                }
                disabled
              />
            </div>
          </div>
        )}

        {/* Search button */}
        {!hasResults && (
          <Button
            className="w-full"
            onClick={() => findMutation.mutate()}
            disabled={isSearching || (!options.search_web && !options.search_linkedin)}
          >
            {isSearching ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Recherche en cours...
              </>
            ) : (
              <>
                <Search className="h-4 w-4 mr-2" />
                Lancer la recherche
              </>
            )}
          </Button>
        )}

        {/* Loading state */}
        {resultLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Results */}
        {hasResults && (
          <>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <span className="font-medium">
                  {existingResult.contacts.length} contact(s) trouvé(s)
                </span>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => findMutation.mutate()}
                disabled={isSearching}
              >
                <Search className="h-4 w-4 mr-1" />
                Relancer
              </Button>
            </div>

            <div className="space-y-2">
              {existingResult.contacts.map((contact, index) => (
                <ContactItem key={index} contact={contact} />
              ))}
            </div>

            {/* Evidence */}
            {existingResult.evidence && existingResult.evidence.length > 0 && (
              <Collapsible open={showEvidence} onOpenChange={setShowEvidence}>
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" size="sm" className="w-full">
                    <Info className="h-4 w-4 mr-2" />
                    {showEvidence ? "Masquer" : "Voir"} les sources ({existingResult.evidence.length})
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent className="mt-2">
                  <div className="p-3 rounded-lg border bg-muted/50 space-y-1 text-sm">
                    {existingResult.evidence.map((evidence, index) => (
                      <div key={index} className="flex items-start gap-2">
                        <span className="text-muted-foreground">•</span>
                        <span>{evidence}</span>
                      </div>
                    ))}
                  </div>
                </CollapsibleContent>
              </Collapsible>
            )}

            {/* Last search info */}
            {existingResult.completed_at && (
              <p className="text-xs text-muted-foreground text-center">
                Dernière recherche: {new Date(existingResult.completed_at).toLocaleString("fr-FR")}
              </p>
            )}
          </>
        )}

        {/* No results state */}
        {existingResult?.status === "completed" && !hasResults && (
          <div className="text-center py-6">
            <AlertCircle className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
            <p className="font-medium mb-1">Aucun contact trouvé</p>
            <p className="text-sm text-muted-foreground">
              Essayez d&apos;élargir les options de recherche
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default ContactFinder;
