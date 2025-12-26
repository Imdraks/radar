"use client";

import React, { useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import {
  FileText,
  ArrowLeft,
  RefreshCw,
  Sparkles,
  Globe,
  Shield,
  AlertTriangle,
  CheckCircle,
  Clock,
  XCircle,
  Loader2,
  ExternalLink,
  Mail,
  Phone,
  MapPin,
  Calendar,
  Euro,
  Link as LinkIcon,
  ChevronDown,
  ChevronUp,
  FileCheck,
  Eye,
  Trash2,
} from "lucide-react";

import {
  dossiersApi,
  DossierDetail,
  DossierEvidence,
  SourceDocumentItem,
  EnrichmentRun,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";

// State badge component
function StateBadge({ state }: { state: string }) {
  const variants: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
    NOT_CREATED: { color: "bg-gray-100 text-gray-700", icon: <FileText className="h-3 w-3" />, label: "Non créé" },
    PROCESSING: { color: "bg-blue-100 text-blue-700", icon: <Loader2 className="h-3 w-3 animate-spin" />, label: "En cours" },
    ENRICHING: { color: "bg-purple-100 text-purple-700", icon: <Globe className="h-3 w-3 animate-pulse" />, label: "Recherche" },
    MERGING: { color: "bg-indigo-100 text-indigo-700", icon: <Loader2 className="h-3 w-3 animate-spin" />, label: "Finalisation" },
    READY: { color: "bg-green-100 text-green-700", icon: <CheckCircle className="h-3 w-3" />, label: "Prêt" },
    FAILED: { color: "bg-red-100 text-red-700", icon: <XCircle className="h-3 w-3" />, label: "Échec" },
  };

  const variant = variants[state] || variants.NOT_CREATED;

  return (
    <Badge className={`${variant.color} flex items-center gap-1 px-3 py-1`}>
      {variant.icon}
      {variant.label}
    </Badge>
  );
}

// Confidence meter
function ConfidenceMeter({ value, label }: { value: number; label: string }) {
  const getColor = () => {
    if (value >= 80) return "bg-green-500";
    if (value >= 60) return "bg-yellow-500";
    if (value >= 40) return "bg-orange-500";
    return "bg-red-500";
  };

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{value}%</span>
      </div>
      <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${getColor()} transition-all`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

// Evidence card
function EvidenceCard({ evidence }: { evidence: DossierEvidence }) {
  return (
    <Card className="border-l-4 border-l-blue-500">
      <CardContent className="pt-4">
        <div className="flex items-start justify-between mb-2">
          <div>
            <Badge variant="outline" className="mb-2">
              {evidence.field_key.replace("_", " ")}
            </Badge>
            <p className="font-medium">{evidence.value || "N/A"}</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge
              className={
                evidence.provenance === "WEB_ENRICHED"
                  ? "bg-purple-100 text-purple-700"
                  : "bg-blue-100 text-blue-700"
              }
            >
              {evidence.provenance === "WEB_ENRICHED" ? (
                <Globe className="h-3 w-3 mr-1" />
              ) : (
                <FileText className="h-3 w-3 mr-1" />
              )}
              {evidence.provenance === "WEB_ENRICHED" ? "Web" : "Source"}
            </Badge>
            <span className="text-sm text-muted-foreground">
              {evidence.confidence}%
            </span>
          </div>
        </div>

        {evidence.evidence_snippet && (
          <div className="bg-muted/50 rounded-md p-3 mt-2">
            <p className="text-sm italic">&ldquo;{evidence.evidence_snippet}&rdquo;</p>
          </div>
        )}

        {evidence.source_url && (
          <a
            href={evidence.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-blue-600 hover:underline mt-2"
          >
            <ExternalLink className="h-3 w-3" />
            {new URL(evidence.source_url).hostname}
          </a>
        )}
      </CardContent>
    </Card>
  );
}

// Extracted fields display
function ExtractedFieldsCard({ fields, evidence }: { fields: DossierDetail["extracted_fields"]; evidence: DossierEvidence[] }) {
  const getEvidenceForField = (fieldKey: string) =>
    evidence.filter((e) => e.field_key === fieldKey);

  const FieldRow = ({
    icon,
    label,
    value,
    fieldKey,
  }: {
    icon: React.ReactNode;
    label: string;
    value: string | number | null | undefined;
    fieldKey: string;
  }) => {
    const fieldEvidence = getEvidenceForField(fieldKey);
    const hasEvidence = fieldEvidence.length > 0;

    return (
      <div className="flex items-start gap-3 py-3 border-b last:border-0">
        <div className="text-muted-foreground mt-0.5">{icon}</div>
        <div className="flex-1">
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="font-medium">
            {value ? String(value) : <span className="text-muted-foreground italic">Non renseigné</span>}
          </p>
        </div>
        {hasEvidence && (
          <Badge variant="outline" className="bg-green-50 text-green-700">
            <Shield className="h-3 w-3 mr-1" />
            Vérifié
          </Badge>
        )}
      </div>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Informations extraites</CardTitle>
        <CardDescription>
          Données structurées extraites des documents sources
        </CardDescription>
      </CardHeader>
      <CardContent>
        <FieldRow
          icon={<Calendar className="h-4 w-4" />}
          label="Date limite"
          value={fields?.deadline_at ? new Date(fields.deadline_at).toLocaleDateString("fr-FR") : null}
          fieldKey="deadline_at"
        />
        <FieldRow
          icon={<Euro className="h-4 w-4" />}
          label="Budget"
          value={
            fields?.budget_amount
              ? `${fields.budget_amount.toLocaleString("fr-FR")} €`
              : fields?.budget_hint
          }
          fieldKey="budget_amount"
        />
        <FieldRow
          icon={<MapPin className="h-4 w-4" />}
          label="Lieu"
          value={
            fields?.location
              ? `${fields.location.city || ""}, ${fields.location.region || ""}`
              : null
          }
          fieldKey="location"
        />
        <FieldRow
          icon={<Mail className="h-4 w-4" />}
          label="Email contact"
          value={fields?.contact_email}
          fieldKey="contact_email"
        />
        <FieldRow
          icon={<Phone className="h-4 w-4" />}
          label="Téléphone"
          value={fields?.contact_phone}
          fieldKey="contact_phone"
        />
        <FieldRow
          icon={<LinkIcon className="h-4 w-4" />}
          label="URL contact"
          value={fields?.contact_url}
          fieldKey="contact_url"
        />
      </CardContent>
    </Card>
  );
}

export default function DossierDetailPage() {
  const router = useRouter();
  const params = useParams();
  const queryClient = useQueryClient();
  const dossierId = params.id as string;

  // Fetch dossier
  const { data: dossier, isLoading: isLoadingDossier } = useQuery({
    queryKey: ["dossier", dossierId],
    queryFn: () => dossiersApi.get(dossierId),
    enabled: !!dossierId,
  });

  // Fetch evidence
  const { data: evidence = [] } = useQuery({
    queryKey: ["dossier-evidence", dossierId],
    queryFn: () => dossiersApi.getEvidence(dossierId),
    enabled: !!dossierId,
  });

  // Fetch sources
  const { data: sources = [] } = useQuery({
    queryKey: ["dossier-sources", dossierId],
    queryFn: () => dossiersApi.getSources(dossierId),
    enabled: !!dossierId,
  });

  // Fetch enrichments
  const { data: enrichments = [] } = useQuery({
    queryKey: ["dossier-enrichments", dossierId],
    queryFn: () => dossiersApi.getEnrichments(dossierId),
    enabled: !!dossierId,
  });

  // Rebuild mutation
  const rebuildMutation = useMutation({
    mutationFn: () =>
      dossiersApi.build(dossier!.opportunity_id, { force_rebuild: true, auto_enrich: true }),
    onSuccess: () => {
      toast.success("Reconstruction du dossier lancée");
      queryClient.invalidateQueries({ queryKey: ["dossier", dossierId] });
    },
    onError: () => {
      toast.error("Erreur lors de la reconstruction");
    },
  });

  // Enrich mutation
  const enrichMutation = useMutation({
    mutationFn: () =>
      dossiersApi.enrich(dossier!.opportunity_id, { auto_merge: true }),
    onSuccess: () => {
      toast.success("Enrichissement web lancé");
      queryClient.invalidateQueries({ queryKey: ["dossier", dossierId] });
    },
    onError: () => {
      toast.error("Erreur lors de l'enrichissement");
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => dossiersApi.delete(dossierId),
    onSuccess: () => {
      toast.success("Dossier supprimé");
      router.push("/dossiers");
    },
    onError: () => {
      toast.error("Erreur lors de la suppression");
    },
  });

  if (isLoadingDossier) {
    return (
      <ProtectedRoute>
        <AppLayout>
          <div className="flex items-center justify-center min-h-screen">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </AppLayout>
      </ProtectedRoute>
    );
  }

  if (!dossier) {
    return (
      <ProtectedRoute>
        <AppLayout>
          <div className="container mx-auto py-12 text-center">
            <h1 className="text-xl font-medium mb-4">Dossier non trouvé</h1>
            <Button onClick={() => router.push("/dossiers")}>Retour aux dossiers</Button>
          </div>
        </AppLayout>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <AppLayout>
        <div className="container mx-auto py-6 px-4">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-start gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold">{dossier.opportunity_title}</h1>
              <StateBadge state={dossier.state} />
            </div>
            {dossier.opportunity_organization && (
              <p className="text-muted-foreground">{dossier.opportunity_organization}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => enrichMutation.mutate()}
            disabled={enrichMutation.isPending || dossier.state !== "READY"}
          >
            {enrichMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Globe className="h-4 w-4 mr-2" />
            )}
            Enrichir
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => rebuildMutation.mutate()}
            disabled={rebuildMutation.isPending}
          >
            {rebuildMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Reconstruire
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" size="sm">
                <Trash2 className="h-4 w-4 mr-2" />
                Supprimer
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Supprimer le dossier ?</AlertDialogTitle>
                <AlertDialogDescription>
                  Cette action est irréversible. Le dossier et toutes ses preuves seront supprimés.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Annuler</AlertDialogCancel>
                <AlertDialogAction onClick={() => deleteMutation.mutate()}>
                  Supprimer
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Scores row */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <Card>
          <CardContent className="pt-4">
            <p className="text-sm text-muted-foreground">Score final</p>
            <p className="text-3xl font-bold">{dossier.score_final}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-sm text-muted-foreground">Score base</p>
            <p className="text-3xl font-bold text-muted-foreground">{dossier.opportunity_score_base}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <ConfidenceMeter value={dossier.confidence_plus} label="Confiance" />
          </CardContent>
        </Card>
      </div>

      {/* Quality flags */}
      {dossier.quality_flags.length > 0 && (
        <Card className="mb-6 border-amber-200 bg-amber-50">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="h-5 w-5 text-amber-600" />
              <span className="font-medium text-amber-800">Alertes qualité</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {dossier.quality_flags.map((flag) => (
                <Badge key={flag} variant="outline" className="bg-white text-amber-700 border-amber-300">
                  {flag.replace(/_/g, " ")}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main content tabs */}
      <Tabs defaultValue="summary" className="space-y-6">
        <TabsList>
          <TabsTrigger value="summary">Résumé</TabsTrigger>
          <TabsTrigger value="fields">Données extraites</TabsTrigger>
          <TabsTrigger value="evidence">
            Preuves ({evidence.length})
          </TabsTrigger>
          <TabsTrigger value="sources">
            Sources ({sources.length})
          </TabsTrigger>
          <TabsTrigger value="history">
            Historique ({enrichments.length})
          </TabsTrigger>
        </TabsList>

        {/* Summary tab */}
        <TabsContent value="summary">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Résumé</CardTitle>
              </CardHeader>
              <CardContent>
                {dossier.summary_short && (
                  <div 
                    className="text-lg font-medium mb-4 prose prose-sm max-w-none"
                    dangerouslySetInnerHTML={{ __html: dossier.summary_short }}
                  />
                )}
                {dossier.summary_long && (
                  <div 
                    className="prose prose-sm max-w-none"
                    dangerouslySetInnerHTML={{ __html: dossier.summary_long }}
                  />
                )}
              </CardContent>
            </Card>

            <div className="space-y-6">
              {/* Key points */}
              {dossier.key_points.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Points clés</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {dossier.key_points.map((point, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <CheckCircle className="h-4 w-4 text-green-500 mt-1 shrink-0" />
                          <span>{point}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {/* Action checklist */}
              {dossier.action_checklist.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Actions à faire</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {dossier.action_checklist.map((action, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <FileCheck className="h-4 w-4 text-blue-500 mt-1 shrink-0" />
                          <span>{action}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </TabsContent>

        {/* Extracted fields tab */}
        <TabsContent value="fields">
          <ExtractedFieldsCard fields={dossier.extracted_fields} evidence={evidence} />

          {/* Requirements & constraints */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
            {dossier.extracted_fields?.exigences && dossier.extracted_fields.exigences.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Exigences</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {dossier.extracted_fields.exigences.map((req, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <AlertTriangle className="h-4 w-4 text-amber-500 mt-1 shrink-0" />
                        <span>{req}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {dossier.extracted_fields?.contraintes && dossier.extracted_fields.contraintes.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Contraintes</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {dossier.extracted_fields.contraintes.map((cons, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <XCircle className="h-4 w-4 text-red-500 mt-1 shrink-0" />
                        <span>{cons}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Evidence tab */}
        <TabsContent value="evidence">
          {evidence.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {evidence.map((ev) => (
                <EvidenceCard key={ev.id} evidence={ev} />
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <Shield className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
                <p className="text-muted-foreground">Aucune preuve disponible</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Sources tab */}
        <TabsContent value="sources">
          {sources.length > 0 ? (
            <div className="space-y-4">
              {sources.map((source) => (
                <Card key={source.id}>
                  <CardContent className="pt-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <Badge className="mb-2">{source.doc_type}</Badge>
                        {source.source_url && (
                          <a
                            href={source.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-sm text-blue-600 hover:underline"
                          >
                            <ExternalLink className="h-3 w-3" />
                            {source.source_url.substring(0, 60)}...
                          </a>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">
                          {source.fetched_at
                            ? new Date(source.fetched_at).toLocaleString("fr-FR")
                            : new Date(source.created_at).toLocaleString("fr-FR")}
                        </p>
                      </div>
                    </div>
                    {source.raw_text_preview && (
                      <div className="mt-3 p-3 bg-muted/50 rounded text-sm font-mono text-xs line-clamp-3">
                        {source.raw_text_preview}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
                <p className="text-muted-foreground">Aucune source disponible</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* History tab */}
        <TabsContent value="history">
          <Card>
            <CardHeader>
              <CardTitle>Historique des opérations</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Processing info */}
                <div className="flex items-center gap-4 p-3 bg-muted/50 rounded">
                  <FileText className="h-5 w-5 text-blue-500" />
                  <div>
                    <p className="font-medium">Analyse automatique</p>
                    <p className="text-sm text-muted-foreground">
                      {dossier.processed_at
                        ? new Date(dossier.processed_at).toLocaleString("fr-FR")
                        : "Non traité"}
                      {dossier.processing_time_ms > 0 && ` · ${(dossier.processing_time_ms / 1000).toFixed(1)}s`}
                    </p>
                  </div>
                </div>

                {/* Enrichment runs */}
                {enrichments.map((run) => (
                  <div key={run.id} className="flex items-start gap-4 p-3 bg-muted/50 rounded">
                    <Globe className="h-5 w-5 text-blue-500 mt-0.5" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">Recherche complémentaire</p>
                        <Badge
                          className={
                            run.status === "SUCCESS"
                              ? "bg-green-100 text-green-700"
                              : run.status === "FAILED"
                              ? "bg-red-100 text-red-700"
                              : "bg-blue-100 text-blue-700"
                          }
                        >
                          {run.status}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {new Date(run.started_at).toLocaleString("fr-FR")}
                        {run.duration_ms && ` · ${(run.duration_ms / 1000).toFixed(1)}s`}
                      </p>
                      <div className="flex flex-wrap gap-2 mt-2">
                        {run.fields_found.map((f) => (
                          <Badge key={f} className="bg-green-50 text-green-700">
                            ✓ {f}
                          </Badge>
                        ))}
                        {run.fields_not_found.map((f) => (
                          <Badge key={f} variant="outline" className="text-muted-foreground">
                            ✗ {f}
                          </Badge>
                        ))}
                      </div>
                      {run.errors.length > 0 && (
                        <p className="text-sm text-red-600 mt-2">{run.errors.join(", ")}</p>
                      )}
                    </div>
                  </div>
                ))}

                {enrichments.length === 0 && !dossier.enriched_at && (
                  <p className="text-center text-muted-foreground py-4">
                    Aucun enrichissement effectué
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
