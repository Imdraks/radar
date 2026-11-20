"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { api } from "@/lib/api";
import { selectedWorkspace } from "@/store/subscriptionStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { clientError } from "@/lib/platform-clients";
type Result = { id: string; name: string; kind: string; url: string };
const labels: Record<string, string> = {
  artist: "Artiste",
  file: "Fichier",
  project: "Projet",
  task: "Tâche",
  deliverable: "Livrable",
  event: "Événement",
  client: "Client",
};
export function GlobalSearch() {
  const [open, setOpen] = useState(false),
    [draft, setDraft] = useState(""),
    [term, setTerm] = useState("");
  const data = useQuery<Result[]>({
    queryKey: ["workspace-search", selectedWorkspace(), term],
    queryFn: async () =>
      (await api.get("/workbench/search", { params: { q: term } })).data,
    enabled: open && term.length >= 2,
    retry: false,
  });
  return (
    <>
      <Button
        variant="ghost"
        size="icon"
        aria-label="Rechercher dans cet espace"
        onClick={() => setOpen(true)}
      >
        <Search size={18} />
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[85dvh] overflow-y-auto">
          <DialogTitle>Rechercher dans cet espace</DialogTitle>
          <DialogDescription>
            Projets, tâches, livrables et fonctionnalités comprises dans votre
            offre. Jusqu’à 10 résultats par catégorie.
          </DialogDescription>
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              setTerm(draft.trim());
            }}
          >
            <Input
              aria-label="Votre recherche"
              minLength={2}
              maxLength={100}
              required
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Un projet, un artiste…"
            />
            <Button>Rechercher</Button>
          </form>
          {data.isFetching && <p role="status">Recherche en cours…</p>}
          {data.isError && <p role="alert">{clientError(data.error)}</p>}
          {data.data && (
            <ul className="divide-y">
              {data.data.map((r) => (
                <li key={r.kind + r.id}>
                  <Link
                    href={r.url}
                    onClick={() => setOpen(false)}
                    className="block rounded-xl p-4 hover:bg-secondary"
                  >
                    <span className="text-xs text-primary">
                      {labels[r.kind] || r.kind}
                    </span>
                    <p className="break-words font-medium">{r.name}</p>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          {data.data?.length === 0 && (
            <p>Aucun résultat dans cet espace pour ces critères.</p>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
