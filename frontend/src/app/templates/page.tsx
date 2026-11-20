"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import {
  selectedWorkspace,
  useSubscriptionStore,
} from "@/store/subscriptionStore";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { clientError } from "@/lib/platform-clients";
type Template = {
  id: number;
  name: string;
  kind: string;
  definition: {
    tasks: { title: string; day: number }[];
    deliverables: { title: string; day: number }[];
  };
};
export default function Templates() {
  const router = useRouter(),
    cache = useQueryClient();
  const events = useSubscriptionStore((s) => s.hasFeature("events"));
  const [name, setName] = useState(""),
    [kind, setKind] = useState("project"),
    [tasks, setTasks] = useState(""),
    [deliverables, setDeliverables] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [selected, setSelected] = useState<number | null>(null),
    [instance, setInstance] = useState(""),
    [start, setStart] = useState(""),
    [end, setEnd] = useState("");
  const key = ["production-templates", selectedWorkspace()];
  const data = useQuery<Template[]>({
    queryKey: key,
    queryFn: async () => (await api.get("/workbench/templates")).data,
    retry: false,
  });
  const lines = (value: string) =>
    value
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean)
      .map((line) => {
        const m = line.match(/^(.*?)\s*\|\s*([+-]?\d+)$/);
        return { title: m ? m[1].trim() : line, day: m ? Number(m[2]) : 0 };
      });
  return (
    <ProtectedRoute>
      <AppLayout>
        <div className="mx-auto max-w-5xl space-y-7">
          <header>
            <p className="radar-eyebrow">Organisation</p>
            <h1 className="mt-2 text-3xl font-semibold">
              Vos modèles de production
            </h1>
            <p className="mt-3 text-muted-foreground">
              Préparez une structure, puis créez un projet ou un événement avec
              ses tâches et livrables. Les responsables, fichiers et budgets ne
              sont pas copiés.
            </p>
          </header>
          {error && (
            <p role="alert" className="text-destructive">
              {error}
            </p>
          )}
          <form
            className="space-y-4 rounded-2xl border bg-card p-5"
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              setError("");
              try {
                await api.post("/workbench/templates", {
                  name,
                  kind,
                  definition: {
                    tasks: lines(tasks),
                    deliverables: lines(deliverables),
                  },
                });
                setName("");
                setTasks("");
                setDeliverables("");
                await cache.invalidateQueries({ queryKey: key });
              } catch (e) {
                setError(clientError(e));
              } finally {
                setBusy(false);
              }
            }}
          >
            <h2 className="text-xl font-semibold">Créer un modèle</h2>
            <Label htmlFor="template-name">Nom du modèle</Label>
            <Input
              id="template-name"
              required
              maxLength={200}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <Label htmlFor="template-kind">Usage</Label>
            <select
              id="template-kind"
              className="h-10 rounded-xl border bg-background px-3"
              value={kind}
              onChange={(e) => setKind(e.target.value)}
            >
              <option value="project">Projet</option>
              {events && <option value="event">Événement</option>}
            </select>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="template-tasks">Tâches · une par ligne</Label>
                <Textarea
                  id="template-tasks"
                  value={tasks}
                  onChange={(e) => setTasks(e.target.value)}
                  maxLength={15000}
                />
              </div>
              <div>
                <Label htmlFor="template-deliverables">
                  Livrables · un par ligne
                </Label>
                <Textarea
                  id="template-deliverables"
                  value={deliverables}
                  onChange={(e) => setDeliverables(e.target.value)}
                  maxLength={15000}
                />
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Écrivez « Brief | -2 » pour une échéance deux jours avant le
              démarrage, ou « Export | 3 » pour trois jours après. Sans
              décalage, l’échéance est placée au démarrage. Vous pourrez les
              ajuster dans le projet.
            </p>
            <Button disabled={busy}>Enregistrer le modèle</Button>
          </form>
          {data.isPending && <p role="status">Chargement…</p>}
          {data.isError && (
            <p role="alert">
              {clientError(data.error)}{" "}
              <Button onClick={() => data.refetch()}>Réessayer</Button>
            </p>
          )}
          {data.data?.length === 0 && (
            <p>Aucun modèle enregistré dans cet espace.</p>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            {data.data?.map((t) => (
              <section
                key={t.id}
                className="space-y-3 rounded-2xl border bg-card p-5"
              >
                <h2 className="break-words text-xl font-semibold">{t.name}</h2>
                <p className="text-sm text-muted-foreground">
                  {t.kind === "event" ? "Événement" : "Projet"} ·{" "}
                  {t.definition.tasks.length} tâches ·{" "}
                  {t.definition.deliverables.length} livrables
                </p>
                <Button
                  variant="outline"
                  onClick={() => {
                    setSelected(t.id);
                    setInstance(t.name);
                  }}
                >
                  Utiliser ce modèle
                </Button>
                {selected === t.id && (
                  <form
                    className="space-y-3 border-t pt-4"
                    onSubmit={async (e) => {
                      e.preventDefault();
                      setBusy(true);
                      setError("");
                      try {
                        const r = await api.post(
                          `/workbench/templates/${t.id}/instantiate`,
                          {
                            name: instance,
                            starts_at: start + ":00",
                            ends_at: end ? end + ":00" : null,
                          },
                        );
                        router.push(r.data.url);
                      } catch (e) {
                        setError(clientError(e));
                      } finally {
                        setBusy(false);
                      }
                    }}
                  >
                    <Label htmlFor="instance-name">
                      Nom de la nouvelle production
                    </Label>
                    <Input
                      id="instance-name"
                      value={instance}
                      required
                      maxLength={200}
                      onChange={(e) => setInstance(e.target.value)}
                    />
                    <Label htmlFor="instance-start">Démarrage · UTC</Label>
                    <Input
                      id="instance-start"
                      type="datetime-local"
                      required
                      value={start}
                      onChange={(e) => setStart(e.target.value)}
                    />
                    {t.kind === "event" && (
                      <>
                        <Label htmlFor="instance-end">Fin · UTC</Label>
                        <Input
                          id="instance-end"
                          type="datetime-local"
                          required
                          value={end}
                          onChange={(e) => setEnd(e.target.value)}
                        />
                      </>
                    )}
                    <Button disabled={busy}>Créer la production</Button>
                  </form>
                )}
              </section>
            ))}
          </div>
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
