"use client";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  RefreshCw,
  Search,
  ShieldCheck,
  Building2,
  UserRound,
  FileText,
} from "lucide-react";
import { AdminLayout, ProtectedRoute } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  activityRequest,
  activityLabel,
  activityTime,
  actorLabel,
  resourceLabels,
  type ActivityEntry,
  type ActivityPage,
  type ActivityFilters,
} from "@/lib/activity";
import { clientError } from "@/lib/platform-clients";

type Filters = {
  q: string;
  author: string;
  action: string;
  resource: string;
  period: string;
  from: string;
  to: string;
};
const empty: Filters = {
  q: "",
  author: "",
  action: "",
  resource: "",
  period: "24",
  from: "",
  to: "",
};
const selectClass = "h-10 w-full rounded-xl border bg-background px-3 text-sm";
function EventIcon({ entry }: { entry: ActivityEntry }) {
  const security = /^(login|logout|mfa\.|password\.|passkey\.|session\.)/.test(
    entry.action,
  );
  const Icon = security
    ? ShieldCheck
    : entry.resource_type === "workspace"
      ? Building2
      : entry.resource_type === "user"
        ? UserRound
        : entry.resource_type
          ? FileText
          : Activity;
  return (
    <span
      aria-hidden="true"
      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary"
    >
      <Icon size={17} />
    </span>
  );
}
function Resource({ entry }: { entry: ActivityEntry }) {
  return (
    <span className="break-all text-xs text-muted-foreground">
      {entry.resource_type
        ? resourceLabels[entry.resource_type] || entry.resource_type
        : "Ressource non renseignée"}
      {entry.resource_id ? ` · ${entry.resource_id}` : ""}
    </span>
  );
}

function Journal() {
  const [draft, setDraft] = useState(empty);
  const [filters, setFilters] = useState(empty);
  const [page, setPage] = useState(1);
  const [auto, setAuto] = useState(false);
  const [selected, setSelected] = useState<ActivityEntry | null>(null);
  const [filterError, setFilterError] = useState("");
  const metadata = useQuery<ActivityFilters>({
    queryKey: ["activity-filter-options"],
    queryFn: () => activityRequest("filters"),
    staleTime: 60000,
    retry: false,
  });
  const params = new URLSearchParams({ page: String(page), limit: "25" });
  if (filters.q) params.set("q", filters.q);
  if (filters.author === "unassigned") params.set("unassigned", "true");
  else if (filters.author) params.set("author_id", filters.author);
  if (filters.action) params.set("action", filters.action);
  if (filters.resource) params.set("resource_type", filters.resource);
  if (filters.period === "custom") {
    if (filters.from) params.set("from_date", filters.from);
    if (filters.to) params.set("to_date", filters.to);
  } else if (filters.period !== "all")
    params.set("since_hours", filters.period);
  const logs = useQuery<ActivityPage>({
    queryKey: ["activity-journal", filters, page],
    queryFn: () => activityRequest("search?" + params),
    retry: false,
    refetchInterval: auto && page === 1 ? 30000 : false,
  });
  useEffect(() => {
    if (logs.data) {
      const max = Math.max(1, Math.ceil(logs.data.total / logs.data.limit));
      if (page > max) setPage(max);
    }
  }, [logs.data, page]);
  const refresh = () => {
    void logs.refetch();
    void metadata.refetch();
  };
  const data = logs.data;
  const summary = data?.summary;
  return (
    <div className="mx-auto max-w-[1440px] space-y-7 p-4 sm:p-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="radar-eyebrow">Administration Radar</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">
            Journal d’activité
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-muted-foreground">
            Retrouvez les actions enregistrées sur la plateforme : connexions,
            sécurité, entreprises et opérations métier.
          </p>
        </div>
        <Button
          variant="outline"
          className="gap-2"
          disabled={logs.isFetching}
          onClick={refresh}
        >
          <RefreshCw
            size={16}
            className={logs.isFetching ? "animate-spin" : ""}
          />
          Actualiser
        </Button>
      </header>
      <form
        className="space-y-5 rounded-2xl border bg-card p-5"
        onSubmit={(event) => {
          event.preventDefault();
          if (draft.period === "custom" && (!draft.from || !draft.to)) {
            setFilterError("Renseignez les deux dates de la période.");
            return;
          }
          if (
            draft.period === "custom" &&
            draft.from &&
            draft.to &&
            draft.from > draft.to
          ) {
            setFilterError("La date de début doit précéder la date de fin.");
            return;
          }
          setFilterError("");
          setFilters({ ...draft, q: draft.q.trim() });
          setPage(1);
        }}
      >
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="activity-search">
              Nom, e-mail, action ou identifiant
            </Label>
            <div className="relative">
              <Search
                size={16}
                className="absolute left-3 top-3 text-muted-foreground"
              />
              <Input
                id="activity-search"
                className="pl-9"
                value={draft.q}
                maxLength={100}
                onChange={(event) =>
                  setDraft({ ...draft, q: event.target.value })
                }
                placeholder="Rechercher dans le journal…"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="activity-author">Auteur</Label>
            <select
              id="activity-author"
              className={selectClass}
              value={draft.author}
              onChange={(event) =>
                setDraft({ ...draft, author: event.target.value })
              }
            >
              <option value="">Tous les auteurs</option>
              <option value="unassigned">Non attribué à un compte</option>
              {metadata.data?.authors.map((author) => (
                <option key={author.id} value={author.id}>
                  {author.name || author.email || `Compte n°${author.id}`}
                  {author.name && author.email ? ` · ${author.email}` : ""}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="activity-period">Période</Label>
            <select
              id="activity-period"
              className={selectClass}
              value={draft.period}
              onChange={(event) =>
                setDraft({ ...draft, period: event.target.value })
              }
            >
              <option value="24">Dernières 24 heures</option>
              <option value="168">7 derniers jours</option>
              <option value="720">30 derniers jours</option>
              <option value="all">Tout l’historique</option>
              <option value="custom">Dates personnalisées</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="activity-action">Action</Label>
            <select
              id="activity-action"
              className={selectClass}
              value={draft.action}
              onChange={(event) =>
                setDraft({ ...draft, action: event.target.value })
              }
            >
              <option value="">Toutes les actions</option>
              {metadata.data?.actions.map((action) => (
                <option key={action} value={action}>
                  {activityLabel(action)}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="activity-resource">Ressource</Label>
            <select
              id="activity-resource"
              className={selectClass}
              value={draft.resource}
              onChange={(event) =>
                setDraft({ ...draft, resource: event.target.value })
              }
            >
              <option value="">Toutes les ressources</option>
              {metadata.data?.resource_types.map((resource) => (
                <option key={resource} value={resource}>
                  {resourceLabels[resource] || resource}
                </option>
              ))}
            </select>
          </div>
          {draft.period === "custom" && (
            <>
              <div className="space-y-2">
                <Label htmlFor="activity-from">Du</Label>
                <Input
                  id="activity-from"
                  type="date"
                  value={draft.from}
                  onChange={(event) =>
                    setDraft({ ...draft, from: event.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="activity-to">Au inclus</Label>
                <Input
                  id="activity-to"
                  type="date"
                  value={draft.to}
                  onChange={(event) =>
                    setDraft({ ...draft, to: event.target.value })
                  }
                />
              </div>
            </>
          )}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
          <p className="text-xs text-muted-foreground">
            Dates affichées et filtrées à l’heure de Paris.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setDraft(empty);
                setFilters(empty);
                setPage(1);
                setFilterError("");
              }}
            >
              Réinitialiser
            </Button>
            <Button>Appliquer les filtres</Button>
          </div>
        </div>
        {filterError && (
          <p role="alert" className="text-sm text-destructive">
            {filterError}
          </p>
        )}
        {metadata.isError && (
          <p role="status" className="text-xs text-muted-foreground">
            Les options de filtre n’ont pas pu être chargées. La recherche reste
            disponible.{" "}
            <button
              type="button"
              className="text-primary underline"
              onClick={() => metadata.refetch()}
            >
              Recharger les options
            </button>
          </p>
        )}
      </form>
      <section
        aria-label="Synthèse des événements filtrés"
        className="grid gap-4 sm:grid-cols-3"
      >
        {[
          ["Événements enregistrés", data?.total],
          ["Comptes ayant une activité", summary?.authors],
          ["Connexions enregistrées", summary?.logins],
        ].map(([label, value]) => (
          <div key={label} className="rounded-2xl border bg-card p-5">
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="mt-3 text-2xl font-semibold">
              {value === undefined ? "—" : value}
            </p>
          </div>
        ))}
      </section>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <p className="text-xs text-muted-foreground">
          {logs.dataUpdatedAt
            ? `Dernier chargement réussi : ${activityTime(new Date(logs.dataUpdatedAt).toISOString(), true)}`
            : "Aucun chargement confirmé."}
        </p>
        <div className="flex items-center gap-3">
          <Label htmlFor="activity-auto" className="text-xs">
            Actualisation automatique · 30 s
          </Label>
          <Switch id="activity-auto" checked={auto} onCheckedChange={setAuto} />
        </div>
      </div>
      {auto && page > 1 && (
        <p role="status" className="text-xs text-muted-foreground">
          Actualisation automatique en pause pendant la consultation des pages
          suivantes.
        </p>
      )}
      {logs.isError && (
        <section
          role="alert"
          className="space-y-3 rounded-2xl border border-destructive/30 bg-card p-5"
        >
          <p className="text-sm">
            {data
              ? "L’actualisation a échoué. Les données du dernier chargement réussi restent affichées."
              : clientError(logs.error)}
          </p>
          <Button variant="outline" onClick={() => logs.refetch()}>
            Réessayer
          </Button>
        </section>
      )}
      {logs.isPending ? (
        <p role="status" className="rounded-2xl border bg-card p-6 text-sm">
          Chargement des événements…
        </p>
      ) : (
        data && (
          <>
            {data.items.length === 0 ? (
              <section className="rounded-2xl border bg-card p-10 text-center">
                <Activity className="mx-auto mb-4 text-primary" />
                <h2 className="font-semibold">
                  Aucun événement pour ces critères
                </h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  Modifiez les filtres ou élargissez la période.
                </p>
              </section>
            ) : (
              <ul className="divide-y overflow-hidden rounded-2xl border bg-card">
                {data.items.map((entry) => (
                  <li
                    key={entry.id}
                    className="flex flex-wrap items-start gap-4 p-5"
                  >
                    <EventIcon entry={entry} />
                    <div className="min-w-0 flex-1 basis-[180px] space-y-2">
                      <h2 className="break-words text-sm font-semibold">
                        {activityLabel(entry.action)}
                      </h2>
                      <p className="break-words text-sm">
                        {actorLabel(entry)}
                        {entry.user_email &&
                          entry.user_email !== actorLabel(entry) && (
                            <span className="ml-2 break-all text-xs text-muted-foreground">
                              {entry.user_email}
                            </span>
                          )}
                      </p>
                      <Resource entry={entry} />
                    </div>
                    <div className="flex flex-wrap items-center gap-3 sm:flex-col sm:items-end">
                      <time
                        dateTime={
                          /Z$|[+-]\d\d:\d\d$/.test(entry.created_at)
                            ? entry.created_at
                            : entry.created_at + "Z"
                        }
                        className="text-xs text-muted-foreground"
                      >
                        {activityTime(entry.created_at)}
                      </time>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelected(entry)}
                        aria-label={`Détails : ${activityLabel(entry.action)}`}
                      >
                        Voir les détails
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <Button
                variant="outline"
                disabled={page === 1 || logs.isFetching}
                onClick={() => setPage((value) => value - 1)}
              >
                Précédent
              </Button>
              <p className="text-xs text-muted-foreground">
                Page {page} sur{" "}
                {Math.max(1, Math.ceil(data.total / data.limit))} · {data.total}{" "}
                événement(s)
              </p>
              <Button
                variant="outline"
                disabled={page * data.limit >= data.total || logs.isFetching}
                onClick={() => setPage((value) => value + 1)}
              >
                Suivant
              </Button>
            </div>
          </>
        )
      )}
      <Dialog
        open={Boolean(selected)}
        onOpenChange={(value) => {
          if (!value) setSelected(null);
        }}
      >
        <DialogContent className="max-h-[90dvh] w-[calc(100%-2rem)] overflow-y-auto sm:max-w-2xl">
          <DialogTitle>Détail de l’événement</DialogTitle>
          <DialogDescription>
            {selected ? activityLabel(selected.action) : "Événement enregistré"}
          </DialogDescription>
          {selected && (
            <div className="space-y-5">
              <dl className="grid gap-4 sm:grid-cols-2">
                {[
                  ["Date et heure", activityTime(selected.created_at, true)],
                  ["Auteur", actorLabel(selected)],
                  ["E-mail", selected.user_email],
                  ["Adresse IP enregistrée", selected.ip_address],
                  ["Action technique", selected.action],
                  ["Identifiant de suivi", selected.user_tracking_id],
                  ["Ressource", selected.resource_type],
                  ["Identifiant de ressource", selected.resource_id],
                  ["Identifiant d’événement", selected.id],
                ].map(([label, value]) => (
                  <div key={label}>
                    <dt className="text-xs text-muted-foreground">{label}</dt>
                    <dd className="mt-2 break-all text-sm">
                      {value || "Non renseigné"}
                    </dd>
                  </div>
                ))}
              </dl>
              <section>
                <h3 className="text-sm font-semibold">
                  Informations enregistrées
                </h3>
                <p className="mt-2 text-xs leading-6 text-muted-foreground">
                  Les valeurs d’authentification sont masquées à la lecture. Les
                  données d’audit d’origine sont conservées.
                </p>
                {selected.details && Object.keys(selected.details).length ? (
                  <pre className="mt-4 max-h-72 overflow-auto whitespace-pre-wrap break-all rounded-xl bg-secondary p-4 text-xs leading-6">
                    {JSON.stringify(selected.details, null, 2)}
                  </pre>
                ) : (
                  <p className="mt-3 text-sm text-muted-foreground">
                    Aucun détail complémentaire enregistré.
                  </p>
                )}
              </section>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
export default function ActivityPage() {
  return (
    <ProtectedRoute>
      <AdminLayout>
        <Journal />
      </AdminLayout>
    </ProtectedRoute>
  );
}
