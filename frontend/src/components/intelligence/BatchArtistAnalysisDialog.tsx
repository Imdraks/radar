"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { 
  Loader2, 
  Users, 
  CheckCircle2,
  XCircle,
  Clock,
  Brain,
  Sparkles,
  Play,
  RotateCcw,
  Music,
} from "lucide-react";

interface ArtistTask {
  name: string;
  taskId: string | null;
  status: "pending" | "processing" | "completed" | "error";
  result?: any;
  error?: string;
}

export function BatchArtistAnalysisDialog() {
  const [open, setOpen] = useState(false);
  const [artistsText, setArtistsText] = useState("");
  const [tasks, setTasks] = useState<ArtistTask[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Parse artists from text (one per line or comma-separated)
  const parseArtists = (text: string): string[] => {
    return text
      .split(/[\n,]+/)
      .map(name => name.trim())
      .filter(name => name.length > 0)
      .filter((name, index, arr) => arr.indexOf(name) === index); // Remove duplicates
  };

  const startAnalysis = async () => {
    const artistNames = parseArtists(artistsText);
    if (artistNames.length === 0) return;

    // Initialize tasks
    const initialTasks: ArtistTask[] = artistNames.map(name => ({
      name,
      taskId: null,
      status: "pending",
    }));
    setTasks(initialTasks);
    setIsRunning(true);
    setCurrentIndex(0);

    // Process each artist sequentially
    for (let i = 0; i < artistNames.length; i++) {
      setCurrentIndex(i);
      
      // Update status to processing
      setTasks(prev => prev.map((t, idx) => 
        idx === i ? { ...t, status: "processing" } : t
      ));

      try {
        // Start the analysis
        const response = await api.post("/ingestion/analyze-artist", {
          artist_name: artistNames[i],
          force_refresh: false,
        });
        
        const taskId = response.data.task_id;
        
        // Update with task ID
        setTasks(prev => prev.map((t, idx) => 
          idx === i ? { ...t, taskId } : t
        ));

        // Poll for completion
        let completed = false;
        let attempts = 0;
        const maxAttempts = 60; // 2 minutes max per artist

        while (!completed && attempts < maxAttempts) {
          await new Promise(resolve => setTimeout(resolve, 2000));
          
          try {
            const statusResponse = await api.get(`/ingestion/task/${taskId}`);
            const taskStatus = statusResponse.data;

            if (taskStatus.ready) {
              completed = true;
              
              if (taskStatus.result?.success || taskStatus.result?.result) {
                setTasks(prev => prev.map((t, idx) => 
                  idx === i ? { 
                    ...t, 
                    status: "completed", 
                    result: taskStatus.result 
                  } : t
                ));
              } else {
                setTasks(prev => prev.map((t, idx) => 
                  idx === i ? { 
                    ...t, 
                    status: "error", 
                    error: taskStatus.result?.error || "Analyse échouée" 
                  } : t
                ));
              }
            }
          } catch (pollError) {
            attempts++;
          }
          
          attempts++;
        }

        if (!completed) {
          setTasks(prev => prev.map((t, idx) => 
            idx === i ? { ...t, status: "error", error: "Timeout" } : t
          ));
        }

      } catch (error: any) {
        setTasks(prev => prev.map((t, idx) => 
          idx === i ? { 
            ...t, 
            status: "error", 
            error: error.message || "Erreur de connexion" 
          } : t
        ));
      }

      // Small delay between artists to avoid rate limiting
      if (i < artistNames.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }

    setIsRunning(false);
  };

  const handleReset = () => {
    setTasks([]);
    setArtistsText("");
    setIsRunning(false);
    setCurrentIndex(0);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case "error":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "processing":
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      default:
        return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  const completedCount = tasks.filter(t => t.status === "completed").length;
  const errorCount = tasks.filter(t => t.status === "error").length;
  const progress = tasks.length > 0 
    ? ((completedCount + errorCount) / tasks.length) * 100 
    : 0;

  const artistCount = parseArtists(artistsText).length;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="gap-2">
          <Users className="h-4 w-4" />
          Analyse Multiple
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-purple-500" />
            Analyse Multiple d'Artistes
          </DialogTitle>
          <DialogDescription>
            Analysez plusieurs artistes en une seule fois. Entrez un nom par ligne.
          </DialogDescription>
        </DialogHeader>

        {tasks.length === 0 ? (
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center justify-between">
                <span>Liste des artistes</span>
                {artistCount > 0 && (
                  <Badge variant="secondary">{artistCount} artiste{artistCount > 1 ? 's' : ''}</Badge>
                )}
              </label>
              <Textarea
                placeholder={`Entrez un artiste par ligne, par exemple:

Ninho
Jul
Aya Nakamura
Damso
SCH
Gazo
Orelsan`}
                value={artistsText}
                onChange={(e) => setArtistsText(e.target.value)}
                className="min-h-[200px] font-mono"
              />
            </div>
            
            <div className="p-4 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-lg">
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-purple-500" />
                Analyse batch inclut
              </h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                  Scan web complet
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                  Données Spotify
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                  Estimation cachet
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                  Score IA & Prédictions
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-3">
                ⏱️ Temps estimé : ~30-60 secondes par artiste
              </p>
            </div>

            <DialogFooter>
              <Button
                onClick={startAnalysis}
                disabled={artistCount === 0}
                className="gap-2"
              >
                <Play className="h-4 w-4" />
                Lancer l'analyse ({artistCount} artiste{artistCount > 1 ? 's' : ''})
              </Button>
            </DialogFooter>
          </div>
        ) : (
          <div className="space-y-4 py-4">
            {/* Progress bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">
                  Progression: {completedCount + errorCount}/{tasks.length}
                </span>
                <span className="font-medium">
                  {Math.round(progress)}%
                </span>
              </div>
              <Progress value={progress} className="h-2" />
            </div>

            {/* Stats */}
            <div className="flex gap-4 text-sm">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                <span>{completedCount} terminé{completedCount > 1 ? 's' : ''}</span>
              </div>
              {errorCount > 0 && (
                <div className="flex items-center gap-2">
                  <XCircle className="h-4 w-4 text-red-500" />
                  <span>{errorCount} erreur{errorCount > 1 ? 's' : ''}</span>
                </div>
              )}
              {isRunning && (
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
                  <span>En cours...</span>
                </div>
              )}
            </div>

            {/* Task list */}
            <ScrollArea className="h-[350px] pr-4">
              <div className="space-y-2">
                {tasks.map((task, index) => (
                  <div 
                    key={index}
                    className={`p-3 rounded-lg border flex items-center justify-between ${
                      task.status === "processing" 
                        ? "border-blue-300 bg-blue-50 dark:bg-blue-900/20" 
                        : task.status === "completed"
                        ? "border-green-200 bg-green-50 dark:bg-green-900/20"
                        : task.status === "error"
                        ? "border-red-200 bg-red-50 dark:bg-red-900/20"
                        : "border-gray-200"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {getStatusIcon(task.status)}
                      <div>
                        <div className="font-medium flex items-center gap-2">
                          <Music className="h-4 w-4 text-purple-500" />
                          {task.name}
                        </div>
                        {task.status === "completed" && task.result?.ai_score && (
                          <div className="text-xs text-muted-foreground mt-1">
                            Score IA: {task.result.ai_score} • 
                            {task.result.result?.financials?.estimated_fee_min?.toLocaleString()}€ - 
                            {task.result.result?.financials?.estimated_fee_max?.toLocaleString()}€
                          </div>
                        )}
                        {task.status === "error" && (
                          <div className="text-xs text-red-600 mt-1">
                            {task.error}
                          </div>
                        )}
                      </div>
                    </div>
                    
                    {task.status === "completed" && (
                      <Badge className="bg-green-500">✓</Badge>
                    )}
                    {task.status === "processing" && (
                      <Badge variant="secondary" className="animate-pulse">
                        Analyse...
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>

            <DialogFooter className="gap-2">
              {!isRunning && (
                <Button
                  variant="outline"
                  onClick={handleReset}
                  className="gap-2"
                >
                  <RotateCcw className="h-4 w-4" />
                  Nouvelle analyse
                </Button>
              )}
              {!isRunning && (
                <Button onClick={() => setOpen(false)}>
                  Fermer
                </Button>
              )}
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
