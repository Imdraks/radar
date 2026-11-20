"use client";

import { RadarSpinner } from '@/components/ui/radar-loader';
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import {
  Plus,
  MoreVertical,
  Pencil,
  Trash,
  RefreshCw,
  Zap,
  Target,
  AlertTriangle,
  Gem,
  Star,
} from "lucide-react";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { scoringApi } from "@/lib/api";
import type { ScoringRule, RuleType } from "@/lib/types";

const RULE_TYPE_CONFIG: Record<RuleType, { icon: React.ComponentType<{ className?: string }>; color: string; label: string }> = {
  urgency: { icon: Zap, color: "text-orange-500", label: "Urgence" },
  event_fit: { icon: Target, color: "text-blue-500", label: "Fit événementiel" },
  quality: { icon: Star, color: "text-yellow-500", label: "Qualité" },
  value: { icon: Gem, color: "text-green-500", label: "Valeur" },
  penalty: { icon: AlertTriangle, color: "text-red-500", label: "Pénalité" },
};

function ScoringContent() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<ScoringRule | null>(null);

  const { data: rules, isLoading } = useQuery<ScoringRule[]>({
    queryKey: ["scoringRules"],
    queryFn: () => scoringApi.getRules(),
  });

  const createMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => scoringApi.createRule(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scoringRules"] });
      setDialogOpen(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
      scoringApi.updateRule(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scoringRules"] });
      setDialogOpen(false);
      setEditingRule(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => scoringApi.deleteRule(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scoringRules"] });
    },
  });

  const recalculateMutation = useMutation({
    mutationFn: () => scoringApi.recalculateAll(),
  });

  const handleSubmit = (data: Record<string, unknown>) => {
    // Parse condition_value as JSON
    if (typeof data.condition_value === "string") {
      try {
        data.condition_value = JSON.parse(data.condition_value as string);
      } catch {
        // Keep as is
      }
    }
    
    if (editingRule) {
      updateMutation.mutate({ id: editingRule.id, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const handleEdit = (rule: ScoringRule) => {
    setEditingRule(rule);
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingRule(null);
  };

  // Group rules by type
  const groupedRules = rules?.reduce((acc, rule) => {
    const type = rule.rule_type;
    if (!acc[type]) acc[type] = [];
    acc[type].push(rule);
    return acc;
  }, {} as Record<string, ScoringRule[]>);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Règles de scoring</h1>
          <p className="text-muted-foreground">
            Configurez le calcul des scores des opportunités
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => recalculateMutation.mutate()}
            disabled={recalculateMutation.isPending}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Recalculer tout
          </Button>
          <Dialog open={dialogOpen} onOpenChange={handleCloseDialog}>
            <DialogTrigger asChild>
              <Button onClick={() => setEditingRule(null)}>
                <Plus className="h-4 w-4 mr-2" />
                Nouvelle règle
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>
                  {editingRule ? "Modifier la règle" : "Nouvelle règle"}
                </DialogTitle>
              </DialogHeader>
              <RuleForm
                rule={editingRule}
                onSubmit={handleSubmit}
                isLoading={createMutation.isPending || updateMutation.isPending}
              />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Rules by type */}
      {isLoading ? (
        <div className="text-center py-12">
          <RadarSpinner className="h-12 w-12 text-primary mx-auto" />
        </div>
      ) : !groupedRules || Object.keys(groupedRules).length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          Aucune règle configurée
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(RULE_TYPE_CONFIG).map(([type, config]) => {
            const typeRules = groupedRules[type];
            if (!typeRules?.length) return null;

            const Icon = config.icon;

            return (
              <Card key={type}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Icon className={`h-5 w-5 ${config.color}`} />
                    {config.label}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {typeRules
                      .sort((a, b) => b.priority - a.priority)
                      .map((rule) => (
                        <div
                          key={rule.id}
                          className="flex items-center justify-between p-3 rounded-lg border"
                        >
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{rule.label || rule.name}</span>
                              {!rule.is_active && (
                                <Badge variant="secondary">Inactif</Badge>
                              )}
                            </div>
                            <p className="text-sm text-muted-foreground">
                              {rule.description}
                            </p>
                          </div>
                          <div className="flex items-center gap-4">
                            <span
                              className={`text-lg font-bold ${
                                rule.points > 0 ? "text-green-600" : "text-red-600"
                              }`}
                            >
                              {rule.points > 0 ? "+" : ""}
                              {rule.points}
                            </span>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon">
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => handleEdit(rule)}>
                                  <Pencil className="h-4 w-4 mr-2" />
                                  Modifier
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  className="text-destructive"
                                  onClick={() => deleteMutation.mutate(rule.id)}
                                >
                                  <Trash className="h-4 w-4 mr-2" />
                                  Supprimer
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </div>
                        </div>
                      ))}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function RuleForm({
  rule,
  onSubmit,
  isLoading,
}: {
  rule: ScoringRule | null;
  onSubmit: (data: Record<string, unknown>) => void;
  isLoading: boolean;
}) {
  const { register, handleSubmit, watch, setValue } = useForm({
    defaultValues: rule
      ? {
          ...rule,
          condition_value: JSON.stringify(rule.condition_value, null, 2),
        }
      : {
          name: "",
          rule_type: "event_fit",
          description: "",
          condition_type: "keywords",
          condition_value: '{"keywords": []}',
          points: 0,
          label: "",
          priority: 50,
          is_active: true,
        },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="name">Nom technique</Label>
          <Input id="name" {...register("name", { required: true })} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="rule_type">Type</Label>
          <Select
            value={watch("rule_type")}
            onValueChange={(v) => setValue("rule_type", v)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="urgency">Urgence</SelectItem>
              <SelectItem value="event_fit">Fit événementiel</SelectItem>
              <SelectItem value="quality">Qualité</SelectItem>
              <SelectItem value="value">Valeur</SelectItem>
              <SelectItem value="penalty">Pénalité</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="label">Libellé affiché</Label>
        <Input id="label" {...register("label")} placeholder="Ex: Deadline < 7 jours" />
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Input id="description" {...register("description")} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="condition_type">Type de condition</Label>
          <Select
            value={watch("condition_type")}
            onValueChange={(v) => setValue("condition_type", v)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="keywords">Mots-clés</SelectItem>
              <SelectItem value="deadline_days">Jours avant deadline</SelectItem>
              <SelectItem value="has_field">Champ présent</SelectItem>
              <SelectItem value="missing_fields">Champs manquants</SelectItem>
              <SelectItem value="organization_type">Type organisation</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="points">Points</Label>
          <Input
            id="points"
            type="number"
            {...register("points", { valueAsNumber: true })}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="condition_value">Valeur de condition (JSON)</Label>
        <textarea
          id="condition_value"
          className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 font-mono"
          {...register("condition_value")}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="priority">Priorité</Label>
          <Input
            id="priority"
            type="number"
            min={0}
            max={100}
            {...register("priority", { valueAsNumber: true })}
          />
        </div>
        <div className="flex items-center gap-2 pt-8">
          <Switch
            id="is_active"
            checked={watch("is_active")}
            onCheckedChange={(v) => setValue("is_active", v)}
          />
          <Label htmlFor="is_active">Règle active</Label>
        </div>
      </div>

      <DialogFooter>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? "Enregistrement..." : rule ? "Modifier" : "Créer"}
        </Button>
      </DialogFooter>
    </form>
  );
}

export default function ScoringPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <ScoringContent />
      </AppLayout>
    </ProtectedRoute>
  );
}
