"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  User,
  Target,
  Plus,
  Edit,
  Trash2,
  RefreshCw,
  Loader2,
  ChevronDown,
  Settings,
  Sliders,
  Save,
} from "lucide-react";
import { AppLayoutWithOnboarding, ProtectedRoute } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toaster";
import { profilesApi } from "@/lib/api";
import type { Profile, ProfileWeights, ProfileObjective } from "@/lib/types";

const OBJECTIVES: { value: ProfileObjective; label: string; emoji: string }[] = [
  { value: "visibility", label: "Visibilité", emoji: "👁️" },
  { value: "revenue", label: "Revenus", emoji: "💰" },
  { value: "networking", label: "Networking", emoji: "🤝" },
  { value: "artist_development", label: "Développement artiste", emoji: "🎤" },
  { value: "brand_building", label: "Image de marque", emoji: "🏷️" },
];

const DEFAULT_WEIGHTS: ProfileWeights = {
  score_weight: 0.3,
  budget_weight: 0.2,
  deadline_weight: 0.2,
  category_weight: 0.15,
  source_weight: 0.15,
};

interface ProfileFormData {
  name: string;
  description: string;
  objectives: ProfileObjective[];
  weights: ProfileWeights;
  criteria: Record<string, unknown>;
}

function ProfileForm({
  initialData,
  onSubmit,
  onCancel,
  isLoading,
}: {
  initialData?: Profile;
  onSubmit: (data: ProfileFormData) => void;
  onCancel: () => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState<ProfileFormData>({
    name: initialData?.name || "",
    description: initialData?.description || "",
    objectives: initialData?.objectives || [],
    weights: initialData?.weights || DEFAULT_WEIGHTS,
    criteria: initialData?.criteria || {},
  });

  const handleObjectiveToggle = (objective: ProfileObjective) => {
    setFormData((prev) => ({
      ...prev,
      objectives: prev.objectives.includes(objective)
        ? prev.objectives.filter((o) => o !== objective)
        : [...prev.objectives, objective],
    }));
  };

  const handleWeightChange = (key: keyof ProfileWeights, value: number) => {
    setFormData((prev) => ({
      ...prev,
      weights: { ...prev.weights, [key]: value / 100 },
    }));
  };

  return (
    <div className="space-y-6">
      {/* Nom et description */}
      <div className="space-y-4">
        <div>
          <Label htmlFor="name">Nom du profil *</Label>
          <Input
            id="name"
            value={formData.name}
            onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
            placeholder="Ex: Festivals électro été"
          />
        </div>
        <div>
          <Label htmlFor="description">Description</Label>
          <Textarea
            id="description"
            value={formData.description}
            onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
            placeholder="Décrivez ce profil..."
            rows={2}
          />
        </div>
      </div>

      {/* Objectifs */}
      <div>
        <Label className="mb-2 block">Objectifs</Label>
        <div className="flex flex-wrap gap-2">
          {OBJECTIVES.map((obj) => (
            <Badge
              key={obj.value}
              variant={formData.objectives.includes(obj.value) ? "default" : "outline"}
              className="cursor-pointer px-3 py-1.5 text-sm"
              onClick={() => handleObjectiveToggle(obj.value)}
            >
              {obj.emoji} {obj.label}
            </Badge>
          ))}
        </div>
      </div>

      {/* Pondérations */}
      <div>
        <Label className="mb-4 block">Pondérations du Fit Score</Label>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Score de base</span>
              <span>{Math.round(formData.weights.score_weight * 100)}%</span>
            </div>
            <Slider
              value={[formData.weights.score_weight * 100]}
              onValueChange={([v]) => handleWeightChange("score_weight", v)}
              max={100}
              step={5}
            />
          </div>
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Budget</span>
              <span>{Math.round(formData.weights.budget_weight * 100)}%</span>
            </div>
            <Slider
              value={[formData.weights.budget_weight * 100]}
              onValueChange={([v]) => handleWeightChange("budget_weight", v)}
              max={100}
              step={5}
            />
          </div>
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Urgence deadline</span>
              <span>{Math.round(formData.weights.deadline_weight * 100)}%</span>
            </div>
            <Slider
              value={[formData.weights.deadline_weight * 100]}
              onValueChange={([v]) => handleWeightChange("deadline_weight", v)}
              max={100}
              step={5}
            />
          </div>
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Catégorie</span>
              <span>{Math.round(formData.weights.category_weight * 100)}%</span>
            </div>
            <Slider
              value={[formData.weights.category_weight * 100]}
              onValueChange={([v]) => handleWeightChange("category_weight", v)}
              max={100}
              step={5}
            />
          </div>
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Source préférée</span>
              <span>{Math.round(formData.weights.source_weight * 100)}%</span>
            </div>
            <Slider
              value={[formData.weights.source_weight * 100]}
              onValueChange={([v]) => handleWeightChange("source_weight", v)}
              max={100}
              step={5}
            />
          </div>
        </div>
      </div>

      {/* Actions */}
      <DialogFooter>
        <Button variant="outline" onClick={onCancel}>
          Annuler
        </Button>
        <Button onClick={() => onSubmit(formData)} disabled={isLoading || !formData.name}>
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          Enregistrer
        </Button>
      </DialogFooter>
    </div>
  );
}

function ProfileCard({
  profile,
  onEdit,
  onDelete,
  onRecompute,
}: {
  profile: Profile;
  onEdit: () => void;
  onDelete: () => void;
  onRecompute: () => void;
}) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5 text-primary" />
              {profile.name}
            </CardTitle>
            {profile.description && (
              <CardDescription className="mt-1">
                {profile.description}
              </CardDescription>
            )}
          </div>
          <div className="flex items-center gap-1">
            <Button size="icon" variant="ghost" onClick={onRecompute} title="Recalculer scores">
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button size="icon" variant="ghost" onClick={onEdit}>
              <Edit className="h-4 w-4" />
            </Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button size="icon" variant="ghost" className="text-destructive">
                  <Trash2 className="h-4 w-4" />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Supprimer ce profil ?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Cette action est irréversible. Tous les scores associés seront supprimés.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Annuler</AlertDialogCancel>
                  <AlertDialogAction onClick={onDelete} className="bg-destructive text-destructive-foreground">
                    Supprimer
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Objectifs */}
        {profile.objectives && profile.objectives.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {profile.objectives.map((obj) => {
              const objInfo = OBJECTIVES.find((o) => o.value === obj);
              return objInfo ? (
                <Badge key={obj} variant="secondary" className="text-xs">
                  {objInfo.emoji} {objInfo.label}
                </Badge>
              ) : null;
            })}
          </div>
        )}

        {/* Weights visualization */}
        <div className="grid grid-cols-5 gap-2 text-xs text-center">
          <div>
            <div className="text-muted-foreground">Score</div>
            <div className="font-semibold">
              {Math.round((profile.weights?.score_weight || 0) * 100)}%
            </div>
          </div>
          <div>
            <div className="text-muted-foreground">Budget</div>
            <div className="font-semibold">
              {Math.round((profile.weights?.budget_weight || 0) * 100)}%
            </div>
          </div>
          <div>
            <div className="text-muted-foreground">Deadline</div>
            <div className="font-semibold">
              {Math.round((profile.weights?.deadline_weight || 0) * 100)}%
            </div>
          </div>
          <div>
            <div className="text-muted-foreground">Catégorie</div>
            <div className="font-semibold">
              {Math.round((profile.weights?.category_weight || 0) * 100)}%
            </div>
          </div>
          <div>
            <div className="text-muted-foreground">Source</div>
            <div className="font-semibold">
              {Math.round((profile.weights?.source_weight || 0) * 100)}%
            </div>
          </div>
        </div>

        {/* Status */}
        <div className="mt-3 pt-3 border-t flex items-center justify-between text-xs text-muted-foreground">
          <span>
            {profile.is_active ? (
              <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                Actif
              </Badge>
            ) : (
              <Badge variant="outline">Inactif</Badge>
            )}
          </span>
          <span>
            Créé le {new Date(profile.created_at).toLocaleDateString("fr-FR")}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

function ProfilesContent() {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [editingProfile, setEditingProfile] = useState<Profile | null>(null);

  // Fetch profiles
  const { data: profiles, isLoading } = useQuery<Profile[]>({
    queryKey: ["profiles"],
    queryFn: profilesApi.getAll,
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: profilesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profiles"] });
      setIsCreateDialogOpen(false);
      addToast({
        title: "Profil créé",
        description: "Le nouveau profil a été créé avec succès",
        type: "success",
      });
    },
    onError: () => {
      addToast({
        title: "Erreur",
        description: "Impossible de créer le profil",
        type: "error",
      });
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
      profilesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profiles"] });
      setEditingProfile(null);
      addToast({
        title: "Profil mis à jour",
        description: "Les modifications ont été enregistrées",
        type: "success",
      });
    },
    onError: () => {
      addToast({
        title: "Erreur",
        description: "Impossible de mettre à jour le profil",
        type: "error",
      });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: profilesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profiles"] });
      addToast({
        title: "Profil supprimé",
        type: "success",
      });
    },
    onError: () => {
      addToast({
        title: "Erreur",
        description: "Impossible de supprimer le profil",
        type: "error",
      });
    },
  });

  // Recompute mutation
  const recomputeMutation = useMutation({
    mutationFn: profilesApi.recompute,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["shortlists"] });
      addToast({
        title: "Scores recalculés",
        description: "Les fit scores ont été mis à jour",
        type: "success",
      });
    },
    onError: () => {
      addToast({
        title: "Erreur",
        description: "Impossible de recalculer les scores",
        type: "error",
      });
    },
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Sliders className="h-8 w-8 text-primary" />
            Profils
          </h1>
          <p className="text-muted-foreground">
            Définissez vos critères de matching pour personnaliser les recommandations
          </p>
        </div>

        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Nouveau profil
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Créer un profil</DialogTitle>
              <DialogDescription>
                Personnalisez vos critères de matching
              </DialogDescription>
            </DialogHeader>
            <ProfileForm
              onSubmit={(data) => createMutation.mutate({
                ...data,
                weights: data.weights as unknown as Record<string, number>,
              })}
              onCancel={() => setIsCreateDialogOpen(false)}
              isLoading={createMutation.isPending}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Profiles grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : profiles && profiles.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {profiles.map((profile) => (
            <ProfileCard
              key={profile.id}
              profile={profile}
              onEdit={() => setEditingProfile(profile)}
              onDelete={() => deleteMutation.mutate(profile.id)}
              onRecompute={() => recomputeMutation.mutate(profile.id)}
            />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <Sliders className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
            <h3 className="font-semibold text-lg mb-2">Aucun profil</h3>
            <p className="text-muted-foreground mb-4">
              Créez votre premier profil pour personnaliser les recommandations
            </p>
            <Button onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Créer un profil
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Edit dialog */}
      <Dialog open={!!editingProfile} onOpenChange={() => setEditingProfile(null)}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Modifier le profil</DialogTitle>
          </DialogHeader>
          {editingProfile && (
            <ProfileForm
              initialData={editingProfile}
              onSubmit={(data) =>
                updateMutation.mutate({ 
                  id: editingProfile.id, 
                  data: { ...data, weights: data.weights as unknown as Record<string, number> }
                })
              }
              onCancel={() => setEditingProfile(null)}
              isLoading={updateMutation.isPending}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function ProfilesPage() {
  return (
    <ProtectedRoute>
      <AppLayoutWithOnboarding>
        <ProfilesContent />
      </AppLayoutWithOnboarding>
    </ProtectedRoute>
  );
}
