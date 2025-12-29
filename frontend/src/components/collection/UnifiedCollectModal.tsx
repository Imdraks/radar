"use client";

import { useState } from "react";
import {
  Search,
  MapPin,
  Euro,
  Calendar,
  Target,
  User,
  Building,
  Hash,
  Loader2,
  X,
  Plus,
  Sparkles,
  Database,
  Bot,
  ArrowRight,
  CheckCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/toaster";
import { useTasksStore } from "@/store/tasks";
import { collectApi } from "@/lib/api";

// Types
interface EntityInput {
  name: string;
  type: "PERSON" | "ORGANIZATION" | "TOPIC";
}

// Constants
const OBJECTIVES = [
  { value: "SPONSOR", label: "Sponsor / Partenariat", icon: "🤝", description: "Trouver des sponsors et partenaires potentiels" },
  { value: "BOOKING", label: "Booking artiste", icon: "🎤", description: "Opportunités de concerts et événements" },
  { value: "PRESS", label: "Presse / Média", icon: "📰", description: "Contacts presse et médias" },
  { value: "VENUE", label: "Lieu / Salle", icon: "🏛️", description: "Salles et espaces événementiels" },
  { value: "SUPPLIER", label: "Prestataires", icon: "🔧", description: "Prestataires techniques et logistiques" },
  { value: "GRANT", label: "Subventions", icon: "💰", description: "Aides et appels à projets" },
];

const ENTITY_TYPES = [
  { value: "PERSON", label: "Personne", icon: User },
  { value: "ORGANIZATION", label: "Organisation", icon: Building },
  { value: "TOPIC", label: "Thématique", icon: Hash },
];

const TIMEFRAMES = [
  { value: 7, label: "7 derniers jours" },
  { value: 30, label: "30 derniers jours" },
  { value: 90, label: "90 derniers jours" },
  { value: 365, label: "1 an" },
];

const REGIONS = [
  "Toutes les régions",
  "Île-de-France",
  "Auvergne-Rhône-Alpes",
  "Nouvelle-Aquitaine",
  "Occitanie",
  "Provence-Alpes-Côte d'Azur",
  "Hauts-de-France",
  "Grand Est",
  "Bretagne",
  "Pays de la Loire",
  "Normandie",
];

const BUDGET_RANGES = [
  { label: "Tous les budgets", min: undefined, max: undefined },
  { label: "< 10 000 €", min: undefined, max: 10000 },
  { label: "10k - 50k €", min: 10000, max: 50000 },
  { label: "50k - 100k €", min: 50000, max: 100000 },
  { label: "100k - 500k €", min: 100000, max: 500000 },
  { label: "> 500 000 €", min: 500000, max: undefined },
];

interface UnifiedCollectModalProps {
  defaultTab?: "standard" | "advanced";
}

export function UnifiedCollectModal({ defaultTab = "standard" }: UnifiedCollectModalProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"standard" | "advanced">(defaultTab);
  const [isLoading, setIsLoading] = useState(false);
  const { addToast } = useToast();
  const { addTask } = useTasksStore();

  // ========== STANDARD COLLECTION STATE ==========
  const [keywords, setKeywords] = useState("");
  const [standardRegion, setStandardRegion] = useState("Toutes les régions");
  const [standardCity, setStandardCity] = useState("");
  const [standardBudgetRange, setStandardBudgetRange] = useState(0);

  // ========== ADVANCED COLLECTION STATE ==========
  const [objective, setObjective] = useState<string>("");
  const [entities, setEntities] = useState<EntityInput[]>([]);
  const [entityInput, setEntityInput] = useState("");
  const [entityType, setEntityType] = useState<"PERSON" | "ORGANIZATION" | "TOPIC">("ORGANIZATION");
  const [secondaryKeywords, setSecondaryKeywords] = useState("");
  const [timeframeDays, setTimeframeDays] = useState(30);
  const [requireContact, setRequireContact] = useState(false);
  const [advancedRegion, setAdvancedRegion] = useState("Toutes les régions");
  const [advancedCity, setAdvancedCity] = useState("");
  const [advancedBudgetRange, setAdvancedBudgetRange] = useState(0);

  // ========== ENTITY HANDLERS ==========
  const addEntity = () => {
    if (entityInput.trim() && entities.length < 5) {
      setEntities([...entities, { name: entityInput.trim(), type: entityType }]);
      setEntityInput("");
    }
  };

  const removeEntity = (index: number) => {
    setEntities(entities.filter((_: EntityInput, i: number) => i !== index));
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addEntity();
    }
  };

  // ========== VALIDATION ==========
  const isStandardValid = keywords.trim().length > 0;
  const isAdvancedValid = objective && entities.length > 0;

  // ========== SUBMIT HANDLERS ==========
  const handleStandardSubmit = async () => {
    if (!isStandardValid) return;
    setIsLoading(true);

    try {
      const budget = BUDGET_RANGES[standardBudgetRange];
      const result = await collectApi.startStandard({
        keywords,
        region: standardRegion !== "Toutes les régions" ? standardRegion : undefined,
        city: standardCity || undefined,
        budget_min: budget.min,
        budget_max: budget.max,
      });

      addTask({
        id: result.run_ids[0] || `standard-${Date.now()}`,
        type: "ingestion",
        title: `Collecte: ${keywords.slice(0, 30)}...`,
        status: "running",
        progress: 5,
        startedAt: new Date().toISOString(),
      });

      addToast({
        title: "Collecte standard lancée !",
        description: `${result.source_count} source(s) • Résultats dans Opportunités`,
        type: "success",
      });

      setIsOpen(false);
      resetStandardForm();
    } catch (error: any) {
      addToast({
        title: "Erreur",
        description: error.response?.data?.detail || error.message,
        type: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleAdvancedSubmit = async () => {
    if (!isAdvancedValid) return;
    setIsLoading(true);

    try {
      const budget = BUDGET_RANGES[advancedBudgetRange];
      const result = await collectApi.startAdvanced({
        objective,
        entities: entities.map((e: EntityInput) => ({ name: e.name, type: e.type })),
        secondary_keywords: secondaryKeywords.split(",").map((k: string) => k.trim()).filter(Boolean),
        timeframe_days: timeframeDays,
        require_contact: requireContact,
        region: advancedRegion !== "Toutes les régions" ? advancedRegion : undefined,
        city: advancedCity || undefined,
        budget_min: budget.min,
        budget_max: budget.max,
      });

      const objectiveLabel = OBJECTIVES.find(o => o.value === objective)?.label || objective;
      const entityNames = entities.map((e: EntityInput) => e.name).join(", ");

      addTask({
        id: result.run_id,
        type: "collection",
        title: `${objectiveLabel}: ${entityNames}`,
        status: "running",
        progress: 5,
        startedAt: new Date().toISOString(),
      });

      addToast({
        title: "Collecte IA lancée !",
        description: `ChatGPT analyse vos cibles • Résultats dans Dossiers`,
        type: "success",
      });

      setIsOpen(false);
      resetAdvancedForm();
    } catch (error: any) {
      addToast({
        title: "Erreur",
        description: error.response?.data?.detail || error.message,
        type: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // ========== RESET HANDLERS ==========
  const resetStandardForm = () => {
    setKeywords("");
    setStandardRegion("Toutes les régions");
    setStandardCity("");
    setStandardBudgetRange(0);
  };

  const resetAdvancedForm = () => {
    setObjective("");
    setEntities([]);
    setEntityInput("");
    setSecondaryKeywords("");
    setTimeframeDays(30);
    setRequireContact(false);
    setAdvancedRegion("Toutes les régions");
    setAdvancedCity("");
    setAdvancedBudgetRange(0);
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button className="gap-2">
          <Search className="h-4 w-4" />
          Nouvelle collecte
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            Lancer une collecte
          </DialogTitle>
          <DialogDescription>
            Choisissez le type de collecte adapté à vos besoins
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={(v: string) => setActiveTab(v as "standard" | "advanced")}>
          <TabsList className="grid w-full grid-cols-2 mb-4">
            <TabsTrigger value="standard" className="gap-2">
              <Database className="h-4 w-4" />
              Standard
            </TabsTrigger>
            <TabsTrigger value="advanced" className="gap-2">
              <Bot className="h-4 w-4" />
              IA (ChatGPT)
            </TabsTrigger>
          </TabsList>

          {/* ========== STANDARD COLLECTION TAB ========== */}
          <TabsContent value="standard" className="space-y-4">
            <Card className="bg-blue-50/50 border-blue-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Database className="h-4 w-4 text-blue-600" />
                  Collecte via vos sources
                </CardTitle>
                <CardDescription className="text-xs">
                  Recherche dans vos sources configurées (RSS, emails, API...) 
                  <br />
                  <span className="font-medium">→ Résultats dans la page Opportunités</span>
                </CardDescription>
              </CardHeader>
            </Card>

            <div className="space-y-4">
              {/* Keywords */}
              <div className="grid gap-2">
                <Label className="flex items-center gap-2 font-semibold">
                  <Search className="h-4 w-4 text-primary" />
                  Mots-clés de recherche *
                </Label>
                <Input
                  placeholder="Ex: festival, concert, marché public, appel d'offres..."
                  value={keywords}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setKeywords(e.target.value)}
                  className={!keywords.trim() ? "border-destructive" : ""}
                />
                <p className="text-xs text-muted-foreground">
                  Séparez plusieurs mots-clés par des virgules
                </p>
              </div>

              {/* Filters */}
              <div className="grid grid-cols-2 gap-4 p-4 border rounded-lg bg-muted/30">
                <div className="grid gap-2">
                  <Label className="flex items-center gap-2 text-sm">
                    <MapPin className="h-3 w-3" />
                    Région
                  </Label>
                  <Select value={standardRegion} onValueChange={setStandardRegion}>
                    <SelectTrigger className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {REGIONS.map((r) => (
                        <SelectItem key={r} value={r}>{r}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid gap-2">
                  <Label className="flex items-center gap-2 text-sm">
                    <MapPin className="h-3 w-3" />
                    Ville
                  </Label>
                  <Input
                    placeholder="Ex: Paris, Lyon..."
                    value={standardCity}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setStandardCity(e.target.value)}
                    className="h-9"
                  />
                </div>

                <div className="grid gap-2 col-span-2">
                  <Label className="flex items-center gap-2 text-sm">
                    <Euro className="h-3 w-3" />
                    Budget
                  </Label>
                  <Select
                    value={standardBudgetRange.toString()}
                    onValueChange={(v: string) => setStandardBudgetRange(parseInt(v))}
                  >
                    <SelectTrigger className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {BUDGET_RANGES.map((b, i) => (
                        <SelectItem key={i} value={i.toString()}>{b.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setIsOpen(false)}>
                Annuler
              </Button>
              <Button 
                onClick={handleStandardSubmit}
                disabled={!isStandardValid || isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Lancement...
                  </>
                ) : (
                  <>
                    <Database className="h-4 w-4 mr-2" />
                    Lancer la collecte
                  </>
                )}
              </Button>
            </DialogFooter>
          </TabsContent>

          {/* ========== ADVANCED COLLECTION TAB ========== */}
          <TabsContent value="advanced" className="space-y-4">
            <Card className="bg-purple-50/50 border-purple-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Bot className="h-4 w-4 text-purple-600" />
                  Collecte intelligente IA
                </CardTitle>
                <CardDescription className="text-xs">
                  ChatGPT recherche des opportunités, contacts et informations stratégiques
                  <br />
                  <span className="font-medium">→ Résultats dans la page Dossiers</span>
                </CardDescription>
              </CardHeader>
            </Card>

            <div className="space-y-4">
              {/* Objective */}
              <div className="grid gap-2">
                <Label className="flex items-center gap-2 font-semibold">
                  <Target className="h-4 w-4 text-primary" />
                  Objectif *
                </Label>
                <Select value={objective} onValueChange={setObjective}>
                  <SelectTrigger className={!objective ? "border-destructive" : ""}>
                    <SelectValue placeholder="Quel est votre objectif ?" />
                  </SelectTrigger>
                  <SelectContent>
                    {OBJECTIVES.map((obj) => (
                      <SelectItem key={obj.value} value={obj.value}>
                        <span className="flex items-center gap-2">
                          <span>{obj.icon}</span>
                          <span>{obj.label}</span>
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {objective && (
                  <p className="text-xs text-muted-foreground">
                    {OBJECTIVES.find(o => o.value === objective)?.description}
                  </p>
                )}
              </div>

              {/* Entities */}
              <div className="grid gap-2">
                <Label className="flex items-center gap-2 font-semibold">
                  <User className="h-4 w-4 text-primary" />
                  Cible(s) *
                </Label>
                <div className="flex gap-2">
                  <Select value={entityType} onValueChange={(v: string) => setEntityType(v as "PERSON" | "ORGANIZATION" | "TOPIC")}>
                    <SelectTrigger className="w-[140px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ENTITY_TYPES.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          <span className="flex items-center gap-2">
                            <type.icon className="h-4 w-4" />
                            {type.label}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input
                    placeholder="Ex: Théodora, Accor, festival rap..."
                    value={entityInput}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEntityInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    className="flex-1"
                  />
                  <Button type="button" variant="outline" size="icon" onClick={addEntity}>
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>

                {entities.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {entities.map((entity, index) => (
                      <Badge key={index} variant="secondary" className="gap-1 pl-2 pr-1">
                        <span className="text-xs opacity-70">
                          {entity.type === "PERSON" ? "👤" : entity.type === "ORGANIZATION" ? "🏢" : "#"}
                        </span>
                        {entity.name}
                        <button
                          onClick={() => removeEntity(index)}
                          className="ml-1 hover:bg-muted rounded-full p-0.5"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}

                {entities.length === 0 && (
                  <p className="text-xs text-destructive">Ajoutez au moins une cible</p>
                )}
              </div>

              {/* Secondary Keywords */}
              <div className="grid gap-2">
                <Label className="flex items-center gap-2">
                  <Search className="h-4 w-4" />
                  Mots-clés secondaires
                </Label>
                <Input
                  placeholder="Ex: rap, concerts, Paris, sponsoring..."
                  value={secondaryKeywords}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSecondaryKeywords(e.target.value)}
                />
              </div>

              {/* Timeframe */}
              <div className="grid gap-2">
                <Label className="flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  Période
                </Label>
                <Select
                  value={timeframeDays.toString()}
                  onValueChange={(v: string) => setTimeframeDays(parseInt(v))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TIMEFRAMES.map((tf) => (
                      <SelectItem key={tf.value} value={tf.value.toString()}>
                        {tf.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Filters */}
              <div className="grid grid-cols-2 gap-4 p-4 border rounded-lg bg-muted/30">
                <div className="grid gap-2">
                  <Label className="flex items-center gap-2 text-sm">
                    <MapPin className="h-3 w-3" />
                    Région
                  </Label>
                  <Select value={advancedRegion} onValueChange={setAdvancedRegion}>
                    <SelectTrigger className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {REGIONS.map((r) => (
                        <SelectItem key={r} value={r}>{r}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid gap-2">
                  <Label className="flex items-center gap-2 text-sm">
                    <MapPin className="h-3 w-3" />
                    Ville
                  </Label>
                  <Input
                    placeholder="Ex: Paris, Lyon..."
                    value={advancedCity}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAdvancedCity(e.target.value)}
                    className="h-9"
                  />
                </div>

                <div className="grid gap-2 col-span-2">
                  <Label className="flex items-center gap-2 text-sm">
                    <Euro className="h-3 w-3" />
                    Budget
                  </Label>
                  <Select
                    value={advancedBudgetRange.toString()}
                    onValueChange={(v: string) => setAdvancedBudgetRange(parseInt(v))}
                  >
                    <SelectTrigger className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {BUDGET_RANGES.map((b, i) => (
                        <SelectItem key={i} value={i.toString()}>{b.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Contact Priority */}
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  <User className="h-5 w-5 text-primary" />
                  <div>
                    <p className="font-medium text-sm">Prioriser les contacts</p>
                    <p className="text-xs text-muted-foreground">
                      Favorise les résultats avec emails et téléphones
                    </p>
                  </div>
                </div>
                <Switch checked={requireContact} onCheckedChange={setRequireContact} />
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setIsOpen(false)}>
                Annuler
              </Button>
              <Button
                onClick={handleAdvancedSubmit}
                disabled={!isAdvancedValid || isLoading}
                className="bg-purple-600 hover:bg-purple-700"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Lancement...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Lancer avec IA
                  </>
                )}
              </Button>
            </DialogFooter>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}

export default UnifiedCollectModal;
