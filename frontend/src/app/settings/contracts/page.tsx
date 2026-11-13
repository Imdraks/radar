"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AppLayout, ProtectedRoute } from "@/components/layout";
import { selectedWorkspace } from "@/store/subscriptionStore";
import { legalFetch, type LegalBundle } from "@/lib/legal-contracts";
interface Acceptance {
  id: number;
  bundle_id: number;
  plan: string;
  commercial_reference: string;
  accepted_at: string;
}
function Content() {
  const workspace = selectedWorkspace();
  const cache = useQueryClient();
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const bundleQuery = useQuery<LegalBundle>({
    queryKey: ["legal-bundle"],
    queryFn: () => legalFetch("current"),
    retry: false,
  });
  const proofs = useQuery<Acceptance[]>({
    queryKey: ["legal-acceptances", workspace],
    queryFn: () => legalFetch(`acceptances?workspace_id=${workspace}`),
    enabled: !!workspace,
    retry: false,
  });
  const bundle = bundleQuery.data?.documents ? bundleQuery.data : null;
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-3xl font-semibold">Contrats de votre agence</h1>
      <p className="text-sm text-muted-foreground">
        Consultez les textes puis, si vous êtes habilité à engager votre
        organisation, enregistrez votre acceptation avec la référence de l’offre
        réellement reçue. Cette étape n’active aucun droit et ne confirme aucun
        paiement.
      </p>
      {bundle ? (
        <form
          className="space-y-5 rounded-xl border bg-card p-5"
          onSubmit={async (e) => {
            e.preventDefault();
            const data = new FormData(e.currentTarget);
            setBusy(true);
            setMessage("");
            try {
              const proof = await legalFetch(
                `acceptances?workspace_id=${workspace}`,
                {
                  method: "POST",
                  body: JSON.stringify({
                    bundle_id: bundle.id,
                    content_hash: bundle.content_hash,
                    plan: data.get("plan"),
                    commercial_reference: data.get("reference"),
                    accepted: true,
                    authorized_representative: true,
                  }),
                },
              );
              setMessage(
                `Acceptation n°${proof.id} enregistrée. Les droits restent soumis à la décision de la plateforme.`,
              );
              await cache.invalidateQueries({
                queryKey: ["legal-acceptances", workspace],
              });
            } catch (error) {
              setMessage((error as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <h2 className="text-lg font-semibold">Version {bundle.version}</h2>
          <Link
            href={`/contracts?version=${bundle.id}`}
            target="_blank"
            rel="noopener"
            className="text-violet-700 underline"
          >
            Lire et télécharger les six documents
          </Link>
          <p className="break-all text-xs text-muted-foreground">
            Empreinte : {bundle.content_hash}
          </p>
          <div>
            <label htmlFor="contract-plan" className="text-sm">
              Offre concernée
            </label>
            <select
              id="contract-plan"
              name="plan"
              required
              className="mt-2 block w-full rounded border bg-background p-3"
            >
              <option value="core">Radar Core</option>
              <option value="premium">Radar Premium</option>
              <option value="business">Radar Business</option>
            </select>
          </div>
          <label className="block text-sm">
            Référence de l’offre ou du bon de commande
            <input
              name="reference"
              required
              minLength={3}
              maxLength={200}
              className="mt-2 block w-full rounded border bg-background p-3"
            />
          </label>
          <label className="flex items-start gap-3 text-sm">
            <input type="checkbox" required className="mt-1" />
            Je déclare être habilité à engager cette organisation et j’accepte
            les documents de cette version pour l’offre référencée ci-dessus.
          </label>
          <p className="text-xs text-muted-foreground">
            Cette acceptation contractuelle est distincte du consentement aux
            cookies. Vérifiez séparément les prix, la durée et les conditions de
            l’offre commerciale.
          </p>
          <button
            disabled={busy || !workspace}
            className="rounded bg-violet-700 px-4 py-2 text-white"
          >
            Enregistrer mon acceptation
          </button>
        </form>
      ) : (
        <p role="status">
          {bundleQuery.isLoading
            ? "Chargement des documents…"
            : "Les documents de production ne sont pas publiés ou sont indisponibles. Aucune acceptation ne peut être enregistrée."}
        </p>
      )}
      {message && <p role="status">{message}</p>}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Acceptations enregistrées</h2>
        {proofs.isError ? (
          <p>
            Consultation réservée à un administrateur du workspace, ou service
            indisponible.
          </p>
        ) : proofs.data?.length ? (
          proofs.data.map((row) => (
            <article className="rounded border p-4 text-sm" key={row.id}>
              <p>
                N°{row.id} · {row.plan} · {row.commercial_reference}
              </p>
              <Link
                className="underline"
                href={`/contracts?version=${row.bundle_id}`}
              >
                Consulter la version acceptée
              </Link>
            </article>
          ))
        ) : (
          <p>Aucune acceptation affichée.</p>
        )}
      </section>
    </div>
  );
}
export default function Page() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <Content />
      </AppLayout>
    </ProtectedRoute>
  );
}
