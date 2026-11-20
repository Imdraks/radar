"use client";

import { SafeHtml } from "@/components/ui/safe-html";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import {
  FileText,
  Send,
  Download,
  Calendar,
  TrendingUp,
  Star,
  Clock,
  Lightbulb,
  CheckCircle,
  Mail,
  MessageSquare,
} from 'lucide-react';
import { RadarSpinner } from '@/components/ui/radar-loader';

interface WeeklyReportData {
  report_id: string;
  generated_at: string;
  period_start: string;
  period_end: string;
  summary: {
    total_opportunities: number;
    new_this_period: number;
    status_changes: number;
    upcoming_deadlines: number;
  };
  highlights: {
    type: string;
    icon: string;
    title: string;
    description: string;
    priority: string;
  }[];
  metrics: {
    total_count: number;
    new_count: number;
    daily_rate: number;
    average_score: number;
    high_score_count: number;
    conversion_rate: number;
    won_count: number;
    lost_count: number;
  };
  recommendations: string[];
  html_content: string;
  markdown_content: string;
}

export function WeeklyReportDialog() {
  const [isOpen, setIsOpen] = useState(false);
  const [sendSuccess, setSendSuccess] = useState(false);

  const { data: report, isLoading, refetch } = useQuery({
    queryKey: ["weekly-report"],
    queryFn: async () => {
      const response = await api.get("/reports/weekly?period_days=7");
      return response.data as WeeklyReportData;
    },
    enabled: isOpen,
  });

  const sendMutation = useMutation({
    mutationFn: async (channels: string[]) => {
      const response = await api.post("/reports/weekly/send", {
        channels,
      });
      return response.data;
    },
    onSuccess: () => {
      setSendSuccess(true);
      setTimeout(() => setSendSuccess(false), 3000);
    },
  });

  const handleDownload = (format: "html" | "markdown") => {
    if (!report) return;

    const content = format === "html" ? report.html_content : report.markdown_content;
    const mimeType = format === "html" ? "text/html" : "text/markdown";
    const extension = format === "html" ? "html" : "md";

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `rapport-hebdo-${new Date().toISOString().slice(0, 10)}.${extension}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">
          <FileText className="h-4 w-4 mr-2" />
          Rapport hebdo
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            Rapport Hebdomadaire
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <RadarSpinner className="h-12 w-12 animate-spin text-primary mb-4" />
            <p className="text-muted-foreground">Génération du rapport...</p>
          </div>
        ) : report ? (
          <div className="space-y-6">
            {/* Period info */}
            <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
              <div className="flex items-center gap-2">
                <Calendar className="h-5 w-5 text-muted-foreground" />
                <span>
                  {formatDate(report.period_start)} - {formatDate(report.period_end)}
                </span>
              </div>
              <Badge variant="secondary">
                ID: {report.report_id}
              </Badge>
            </div>

            {/* Highlights */}
            <div className="grid gap-3 md:grid-cols-2">
              {report.highlights.map((highlight, index) => (
                <Card
                  key={index}
                  className={`${
                    highlight.priority === "warning"
                      ? "border-orange-200 bg-orange-50 dark:bg-orange-900/20"
                      : highlight.priority === "success"
                      ? "border-green-200 bg-green-50 dark:bg-green-900/20"
                      : ""
                  }`}
                >
                  <CardContent className="pt-4">
                    <div className="flex items-start gap-3">
                      <span className="text-2xl">{highlight.icon}</span>
                      <div>
                        <p className="font-medium">{highlight.title}</p>
                        <p className="text-sm text-muted-foreground">
                          {highlight.description}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Metrics */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Métriques clés
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                    <p className="text-2xl font-bold text-blue-600">
                      {report.metrics.new_count}
                    </p>
                    <p className="text-sm text-muted-foreground">Nouvelles</p>
                  </div>
                  <div className="text-center p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                    <p className="text-2xl font-bold text-green-600">
                      {report.metrics.high_score_count}
                    </p>
                    <p className="text-sm text-muted-foreground">Score élevé</p>
                  </div>
                  <div className="text-center p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                    <p className="text-2xl font-bold text-purple-600">
                      {report.metrics.average_score}/10
                    </p>
                    <p className="text-sm text-muted-foreground">Score moyen</p>
                  </div>
                  <div className="text-center p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                    <p className="text-2xl font-bold text-orange-600">
                      {report.metrics.conversion_rate}%
                    </p>
                    <p className="text-sm text-muted-foreground">Conversion</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Recommendations */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Lightbulb className="h-4 w-4" />
                  Recommandations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {report.recommendations.map((rec, index) => (
                    <li key={index} className="flex items-start gap-2 text-sm">
                      <Star className="h-4 w-4 mt-0.5 text-yellow-500 shrink-0" />
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            {/* Preview */}
            <Tabs defaultValue="html">
              <TabsList>
                <TabsTrigger value="html">Aperçu HTML</TabsTrigger>
                <TabsTrigger value="markdown">Markdown</TabsTrigger>
              </TabsList>
              <TabsContent value="html" className="mt-4">
                <SafeHtml className="border rounded-lg p-4 bg-white dark:bg-neutral-950 max-h-96 overflow-y-auto" html={report.html_content} />
              </TabsContent>
              <TabsContent value="markdown" className="mt-4">
                <pre className="border rounded-lg p-4 bg-muted max-h-96 overflow-y-auto text-sm whitespace-pre-wrap">
                  {report.markdown_content}
                </pre>
              </TabsContent>
            </Tabs>

            {/* Actions */}
            <div className="flex flex-wrap gap-2 justify-end border-t pt-4">
              <Button
                variant="outline"
                onClick={() => handleDownload("html")}
              >
                <Download className="h-4 w-4 mr-2" />
                Télécharger HTML
              </Button>
              <Button
                variant="outline"
                onClick={() => handleDownload("markdown")}
              >
                <Download className="h-4 w-4 mr-2" />
                Télécharger Markdown
              </Button>
              <Button
                onClick={() => sendMutation.mutate(["email"])}
                disabled={sendMutation.isPending || sendSuccess}
              >
                {sendMutation.isPending ? (
                  <RadarSpinner className="h-4 w-4 mr-2 animate-spin" />
                ) : sendSuccess ? (
                  <CheckCircle className="h-4 w-4 mr-2 text-green-500" />
                ) : (
                  <Send className="h-4 w-4 mr-2" />
                )}
                {sendSuccess ? "Envoyé !" : "Envoyer par email"}
              </Button>
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>Impossible de générer le rapport</p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// Quick report card for dashboard
export function WeeklyReportCard() {
  const { data: report, isLoading } = useQuery({
    queryKey: ["weekly-report-preview"],
    queryFn: async () => {
      const response = await api.get("/reports/weekly?period_days=7");
      return response.data as WeeklyReportData;
    },
    staleTime: 10 * 60 * 1000, // Cache 10 minutes
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <RadarSpinner className="h-6 w-6 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  if (!report) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center justify-between">
          <span className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Résumé de la semaine
          </span>
          <WeeklyReportDialog />
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 text-center">
          <div>
            <p className="text-2xl font-bold text-blue-600">
              {report.summary.new_this_period}
            </p>
            <p className="text-xs text-muted-foreground">Nouvelles</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-orange-600">
              {report.summary.upcoming_deadlines}
            </p>
            <p className="text-xs text-muted-foreground">Deadlines</p>
          </div>
        </div>
        {report.highlights[0] && (
          <div className="mt-4 p-3 bg-muted rounded-lg text-sm">
            <span className="mr-2">{report.highlights[0].icon}</span>
            {report.highlights[0].title}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
