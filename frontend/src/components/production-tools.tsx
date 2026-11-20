"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { selectedWorkspace } from "@/store/subscriptionStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { clientError } from "@/lib/platform-clients";
import { activityTime } from "@/lib/activity";
export { GlobalSearch } from "./workspace-search";

type Deliverable = {
  id: number;
  name: string;
  has_link: boolean;
  status: string;
};
type Review = {
  id: number;
  status: string;
  reviewer_name: string | null;
  feedback: string | null;
  expires_at: string;
};
export function ProductionConnections({ projectId }: { projectId: number }) {
  const [selected, setSelected] = useState(""),
    [url, setUrl] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const base = ["production-connections", selectedWorkspace(), projectId];
  const links = useQuery<{
    event_id: number | null;
    client_id: number | null;
    client_url: string | null;
  }>({
    queryKey: base,
    queryFn: async () =>
      (await api.get(`/workbench/projects/${projectId}/connections`)).data,
    retry: false,
  });
  const deliverables = useQuery<Deliverable[]>({
    queryKey: [...base, "deliverables"],
    queryFn: async () =>
      (
        await api.get(
          `/workbench/projects/${projectId}/reviewable-deliverables`,
        )
      ).data,
    retry: false,
  });
  const reviews = useQuery<Review[]>({
    queryKey: [...base, "reviews", selected],
    queryFn: async () =>
      (await api.get(`/workbench/deliverables/${selected}/reviews`)).data,
    enabled: !!selected,
    retry: false,
  });
  return (
    <section className="my-6 space-y-4 rounded-2xl border bg-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Les liens de votre production</h2>
        <div className="flex flex-wrap gap-4 text-sm text-primary">
          <Link href="/templates" className="underline">
            Modèles de production
          </Link>
          {links.data?.event_id && (
            <Link href={`/events/${links.data.event_id}`} className="underline">
              Événement et artistes
            </Link>
          )}
          {links.data?.client_id && (
            <Link
              href={links.data?.client_url || "/clients"}
              className="underline"
            >
              Gestion du client
            </Link>
          )}
        </div>
      </div>
      <p className="text-sm text-muted-foreground">
        Partagez une version d’un livrable pour obtenir une validation externe.
        Le lien expire sous 7 jours et peut être révoqué. Créer un nouveau lien
        désactive le précédent.
      </p>
      {(error || links.isError || deliverables.isError || reviews.isError) && (
        <p role="alert" className="text-sm text-destructive">
          {error ||
            clientError(links.error || deliverables.error || reviews.error)}
        </p>
      )}
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-0 flex-1 space-y-2">
          <Label htmlFor="review-deliverable">Livrable à faire valider</Label>
          <select
            id="review-deliverable"
            className="h-10 w-full rounded-xl border bg-background px-3 text-sm"
            value={selected}
            onChange={(e) => {
              setSelected(e.target.value);
              setUrl("");
              setError("");
            }}
          >
            <option value="">Choisir un livrable</option>
            {deliverables.data?.map((d) => (
              <option key={d.id} value={d.id} disabled={!d.has_link}>
                {d.name}
                {!d.has_link ? " · ajoutez un lien dans Livrables" : ""}
              </option>
            ))}
          </select>
        </div>
        <Button
          disabled={!selected || busy}
          onClick={async () => {
            setBusy(true);
            setError("");
            try {
              const r = await api.post(
                `/workbench/deliverables/${selected}/reviews`,
                { expires_in_days: 7 },
              );
              setUrl(r.data.url);
              await reviews.refetch();
            } catch (e) {
              setError(clientError(e));
            } finally {
              setBusy(false);
            }
          }}
        >
          Créer un lien de validation
        </Button>
      </div>
      {url && (
        <div className="space-y-2 rounded-xl bg-primary/5 p-4">
          <Label htmlFor="review-url">
            Lien confidentiel à transmettre au client
          </Label>
          <Input
            id="review-url"
            readOnly
            value={url}
            onFocus={(e) => e.target.select()}
          />
          <Button
            variant="outline"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(url);
              } catch {
                setError(
                  "Sélectionnez et copiez le lien dans le champ ci-dessus.",
                );
              }
            }}
          >
            Copier le lien
          </Button>
          <p className="text-xs text-muted-foreground">
            Ce lien est affiché une seule fois. Aucun e-mail n’est envoyé
            automatiquement.
          </p>
        </div>
      )}
      {selected &&
        reviews.data?.map((r) => (
          <div
            key={r.id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-xl border p-3"
          >
            <div className="min-w-0 break-words text-sm">
              <strong>
                {r.status === "pending"
                  ? "En attente"
                  : r.status === "approved"
                    ? "Validé"
                    : r.status === "changes"
                      ? "Modifications demandées"
                      : "Révoqué"}
              </strong>
              <p className="text-xs text-muted-foreground">
                Expiration : {activityTime(r.expires_at)}
              </p>
              {r.reviewer_name && <p>Identité déclarée : {r.reviewer_name}</p>}
              {r.feedback && (
                <p className="whitespace-pre-wrap">{r.feedback}</p>
              )}
            </div>
            {r.status === "pending" && (
              <Button
                variant="outline"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  try {
                    await api.post(`/workbench/reviews/${r.id}/revoke`);
                    setUrl("");
                    await reviews.refetch();
                  } catch (e) {
                    setError(clientError(e));
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Révoquer
              </Button>
            )}
          </div>
        ))}
    </section>
  );
}
