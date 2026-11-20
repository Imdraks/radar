"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { activityTime } from "@/lib/activity";
import { selectedWorkspace } from "@/store/subscriptionStore";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { clientError } from "@/lib/platform-clients";
type Status = {
  checked_at: string;
  notice: string;
  providers: { id: string; name: string; state: string; scope: string }[];
  observations: {
    source: string;
    status: string;
    collected_at: string;
    expires_at: string;
    stale: boolean;
    error_code: string | null;
  }[];
  jobs: {
    id: string;
    status: string;
    step: string | null;
    updated_at: string;
    error_code: string | null;
  }[];
};
const labels: Record<string, string> = {
  configured_unverified: "Configuré · disponibilité à vérifier",
  not_configured: "Configuration requise",
  not_connected: "Non connecté",
  authorization_present: "Autorisation enregistrée · accès à vérifier",
  authorization_expired: "Autorisation expirée · reconnexion possible",
  unknown: "État indisponible",
};
export default function Integrations() {
  const data = useQuery<Status>({
    queryKey: ["integration-status", selectedWorkspace()],
    queryFn: async () => (await api.get("/integrations/status")).data,
    retry: false,
  });
  return (
    <ProtectedRoute>
      <AppLayout>
        <div className="mx-auto max-w-5xl space-y-6">
          <header className="flex flex-wrap justify-between gap-3">
            <div>
              <p className="radar-eyebrow">Administration</p>
              <h1 className="mt-2 text-3xl font-semibold">Vos intégrations</h1>
            </div>
            <Button
              variant="outline"
              disabled={data.isFetching}
              onClick={() => data.refetch()}
            >
              Actualiser
            </Button>
          </header>
          <p className="text-muted-foreground">
            Distinguez la configuration, les autorisations et les résultats
            effectivement collectés.
          </p>
          {data.isPending && <p role="status">Chargement…</p>}
          {data.isError && <p role="alert">{clientError(data.error)}</p>}
          {data.data && (
            <>
              <p className="rounded-2xl border bg-card p-5 text-sm">
                {data.data.notice}
              </p>
              <div className="grid gap-4 sm:grid-cols-2">
                {data.data.providers.map((p) => (
                  <section
                    key={p.id}
                    className="space-y-3 rounded-2xl border bg-card p-5"
                  >
                    <h2 className="font-semibold">{p.name}</h2>
                    <p className="text-sm">{labels[p.state] || p.state}</p>
                    <p className="text-xs text-muted-foreground">
                      Périmètre : {p.scope}
                    </p>
                    {["drive", "calendar"].includes(p.id) && (
                      <Link
                        href="/workspace/settings"
                        className="inline-block text-sm text-primary underline"
                      >
                        Gérer la connexion Google
                      </Link>
                    )}
                  </section>
                ))}
              </div>
              <section className="space-y-3">
                <h2 className="text-xl font-semibold">
                  Dernières collectes de cet espace
                </h2>
                {data.data.observations.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    Aucune observation enregistrée. Aucun résultat fournisseur
                    n’est présumé.
                  </p>
                )}
                {data.data.observations.map((o, i) => (
                  <div
                    key={i}
                    className="rounded-xl border bg-card p-4 text-sm"
                  >
                    <strong>{o.source}</strong> · {o.status} ·{" "}
                    {o.stale ? "Données expirées" : "Validité locale en cours"}
                    <p className="mt-2 text-xs text-muted-foreground">
                      Collecte : {activityTime(o.collected_at)} · Expiration :{" "}
                      {activityTime(o.expires_at)}
                      {o.error_code ? ` · Code : ${o.error_code}` : ""}
                    </p>
                  </div>
                ))}
              </section>
              <section className="space-y-3">
                <h2 className="text-xl font-semibold">
                  Traitements artistiques récents
                </h2>
                {data.data.jobs.length === 0 && (
                  <p>Aucun traitement enregistré.</p>
                )}
                {data.data.jobs.map((j) => (
                  <div
                    key={j.id}
                    className="break-words rounded-xl border bg-card p-4 text-sm"
                  >
                    {j.status} · {j.step || "Étape non renseignée"} ·{" "}
                    {activityTime(j.updated_at)}
                    {j.error_code ? ` · ${j.error_code}` : ""}
                  </div>
                ))}
              </section>
            </>
          )}
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
