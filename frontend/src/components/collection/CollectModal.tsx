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
  Contact,
  Loader2,
  X,
  Plus,
  Sparkles,
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
import { useToast } from "@/components/ui/toaster";
import { useTasksStore } from "@/store/tasks";

// Types
export interface EntityInput {
  name: string;
  type: "PERSON" | "ORGANIZATION" | "TOPIC";
}

export interface CollectParams {
  objective: string;
  entities: EntityInput[];
  secondaryKeywords: string[];
  timeframeDays: number;
  requireContact: boolean;
  region: string;
  city: string;
  budgetRange: number;
}

export interface CollectResponse {
  run_id: string;
  source_count: number;
  task_ids: string[];
  entities_created: string[];
  message: string;
}

// Constants
const OBJECTIVES = [
  { value: "SPONSOR", label: "Sponsor / Partenariat", icon: "🤝" },
  { value: "BOOKING", label: "Booking artiste", icon: "🎤" },
  { value: "PRESS", label: "Presse / Média", icon: "📰" },
  { value: "VENUE", label: "Lieu / Salle", icon: "🏛️" },
  { value: "SUPPLIER", label: "Prestataires", icon: "🔧" },
  { value: "GRANT", label: "Subventions / Appels à projets", icon: "💰" },
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
  "Bourgogne-Franche-Comté",
  "Centre-Val de Loire",
  "Corse",
];

const BUDGET_RANGES = [
  { label: "Tous les budgets", min: undefined, max: undefined },
  { label: "< 10 000 €", min: undefined, max: 10000 },
  { label: "10k - 50k €", min: 10000, max: 50000 },
  { label: "50k - 100k €", min: 50000, max: 100000 },
  { label: "100k - 500k €", min: 100000, max: 500000 },
  { label: "> 500 000 €", min: 500000, max: undefined },
];

interface CollectModalProps {
  onCollect: (params: CollectParams) => Promise<CollectResponse>;
  isCollecting?: boolean;
}

export function CollectModal({ onCollect, isCollecting = false }: CollectModalProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { addToast } = useToast();
  const { addTask, updateTask } = useTasksStore();
  
  // Form state
  const [objective, setObjective] = useState<string>("");
  const [entities, setEntities] = useState<EntityInput[]>([]);
  const [entityInput, setEntityInput] = useState("");
  const [entityType, setEntityType] = useState<"PERSON" | "ORGANIZATION" | "TOPIC">("PERSON");
  const [secondaryKeywords, setSecondaryKeywords] = useState("");
  const [timeframeDays, setTimeframeDays] = useState(30);
  const [requireContact, setRequireContact] = useState(false);
  const [region, setRegion] = useState("Toutes les régions");
  const [city, setCity] = useState("");
  const [budgetRange, setBudgetRange] = useState(0);
  
  // Validation
  const isValid = objective && entities.length > 0;
  
  const addEntity = () => {
    if (entityInput.trim() && entities.length < 10) {
      setEntities([...entities, { name: entityInput.trim(), type: entityType }]);
      setEntityInput("");
    }
  };
  
  const removeEntity = (index: number) => {
    setEntities(entities.filter((_, i) => i !== index));
  };
  
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addEntity();
    }
  };
  
  const handleSubmit = async () => {
    if (!isValid) return;
    
    setIsLoading(true);
    
    const params: CollectParams = {
      objective,
      entities,
      secondaryKeywords: secondaryKeywords.split(",").map(k => k.trim()).filter(Boolean),
      timeframeDays,
      requireContact,
      region: region !== "Toutes les régions" ? region : "",
      city,
      budgetRange,
    };
    
    try {
      const result = await onCollect(params);
      
      if (result.source_count === 0) {
        addToast({
          title: "Aucune source active",
          description: "Configurez des sources dans l'onglet Sources",
          type: "warning",
        });
      } else {
        // Add task to background tasks store
        const objectiveLabel = OBJECTIVES.find(o => o.value === objective)?.label || objective;
        const entityNames = entities.map(e => e.name).join(", ");
        
        addTask({
          id: result.run_id,
          type: "collection",
          title: `${objectiveLabel}: ${entityNames}`,
          status: "running",
          progress: 5,
          startedAt: new Date().toISOString(),
        });
        
        addToast({
          title: "Collecte lancée !",
          description: `${result.source_count} source(s) • Suivi en arrière-plan`,
          type: "success",
        });
        setIsOpen(false);
        resetForm();
      }
    } catch (error: any) {
      addToast({
        title: "Erreur de collecte",
        description: error.response?.data?.detail || error.message,
        type: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  const resetForm = () => {
    setObjective("");
    setEntities([]);
    setEntityInput("");
    setSecondaryKeywords("");
    setTimeframeDays(30);
    setRequireContact(false);
    setRegion("Toutes les régions");
    setCity("");
    setBudgetRange(0);
  };
  
  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button className="gap-2">
          <Sparkles className="h-4 w-4" />
          Collecte avancée
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            Configurer la collecte
          </DialogTitle>
          <DialogDescription>
            Définissez votre objectif et vos cibles pour obtenir des dossiers exploitables
          </DialogDescription>
        </DialogHeader>
        
        <div className="grid gap-5 py-4">
          {/* Objectif (obligatoire) */}
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
                      {obj.label}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          {/* Cibles / Entités (obligatoire) */}
          <div className="grid gap-2">
            <Label className="flex items-center gap-2 font-semibold">
              <User className="h-4 w-4 text-primary" />
              Cible principale *
            </Label>
            <div className="flex gap-2">
              <Select value={entityType} onValueChange={(v) => setEntityType(v as any)}>
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
                placeholder="Ex: Théodora, Nayra, Accor, festival rap..."
                value={entityInput}
                onChange={(e) => setEntityInput(e.target.value)}
                onKeyPress={handleKeyPress}
                className="flex-1"
              />
              <Button type="button" variant="outline" size="icon" onClick={addEntity}>
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            
            {/* Entity chips */}
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
              <p className="text-xs text-destructive">
                Ajoutez au moins une cible
              </p>
            )}
          </div>
          
          {/* Mots-clés secondaires (optionnel) */}
          <div className="grid gap-2">
            <Label className="flex items-center gap-2">
              <Search className="h-4 w-4" />
              Mots-clés secondaires
            </Label>
            <Input
              placeholder="Ex: rap, concerts, Paris, sponsoring..."
              value={secondaryKeywords}
              onChange={(e) => setSecondaryKeywords(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Séparez par des virgules
            </p>
          </div>
          
          {/* Période (obligatoire) */}
          <div className="grid gap-2">
            <Label className="flex items-center gap-2 font-semibold">
              <Calendar className="h-4 w-4 text-primary" />
              Période *
            </Label>
            <Select 
              value={timeframeDays.toString()} 
              onValueChange={(v) => setTimeframeDays(parseInt(v))}
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
          
          {/* Filtres supplémentaires - pliable */}
          <div className="border rounded-lg p-4 bg-muted/30">
            <p className="text-sm font-medium mb-3 text-muted-foreground">
              Filtres optionnels
            </p>
            <div className="grid grid-cols-2 gap-4">
              {/* Région */}
              <div className="grid gap-2">
                <Label className="flex items-center gap-2 text-sm">
                  <MapPin className="h-3 w-3" />
                  Région
                </Label>
                <Select value={region} onValueChange={setRegion}>
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
              
              {/* Ville */}
              <div className="grid gap-2">
                <Label className="flex items-center gap-2 text-sm">
                  <MapPin className="h-3 w-3" />
                  Ville
                </Label>
                <Input
                  placeholder="Ex: Paris, Lyon..."
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  className="h-9"
                />
              </div>
              
              {/* Budget */}
              <div className="grid gap-2 col-span-2">
                <Label className="flex items-center gap-2 text-sm">
                  <Euro className="h-3 w-3" />
                  Budget
                </Label>
                <Select 
                  value={budgetRange.toString()} 
                  onValueChange={(v) => setBudgetRange(parseInt(v))}
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
          
          {/* Toggle: Priorité contacts */}
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-3">
              <Contact className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium text-sm">Prioriser les résultats avec contact</p>
                <p className="text-xs text-muted-foreground">
                  Favorise les sources contenant des emails, booking, presse...
                </p>
              </div>
            </div>
            <Switch
              checked={requireContact}
              onCheckedChange={setRequireContact}
            />
          </div>
        </div>
        
        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => setIsOpen(false)}>
            Annuler
          </Button>
          <Button 
            onClick={handleSubmit} 
            disabled={!isValid || isLoading || isCollecting}
          >
            {isLoading || isCollecting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Lancement...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4 mr-2" />
                Lancer la collecte
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default CollectModal;
