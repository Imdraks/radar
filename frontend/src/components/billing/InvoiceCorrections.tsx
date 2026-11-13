"use client";
import { useState, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { workspaceFetch } from "@/lib/workspace-fetch";
import { selectedWorkspace } from "@/store/subscriptionStore";
interface Credit {
  id: number;
  reference: string;
  reason: string;
  total: string;
}
async function billing(path: string, init?: RequestInit) {
  const token = localStorage.getItem("access_token");
  const response = await workspaceFetch(`/api/v1/billing/${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      typeof body.detail === "string" ? body.detail : "Opération indisponible",
    );
  }
  return response;
}
function download(response: Response, name: string) {
  return response.blob().then((blob) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  });
}
export function InvoiceCorrections({
  invoiceId,
  status,
  credited,
  onChanged,
}: {
  invoiceId: number;
  status: string;
  credited: boolean;
  onChanged: () => void;
}) {
  const workspace = selectedWorkspace();
  const cache = useQueryClient();
  const key = useRef("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const notes = useQuery<Credit[]>({
    queryKey: ["invoice-credits", workspace, invoiceId],
    queryFn: async () =>
      (await billing(`invoices/${invoiceId}/credit-notes`)).json(),
  });
  const canIssue =
    !credited &&
    !["DRAFT", "CANCELLED"].includes(status) &&
    Array.isArray(notes.data) &&
    notes.data.length === 0;
  return (
    <section className="space-y-4 rounded-xl border bg-card p-5">
      <h2 className="text-lg font-semibold">Corrections et transmission</h2>
      <p className="text-sm text-muted-foreground">
        Une facture émise reste conservée. Un avoir total reprend ses montants
        et ses mentions d’origine. Il ne réalise aucun remboursement bancaire.
        Les avoirs partiels et les cas fiscaux particuliers nécessitent un
        traitement adapté.
      </p>
      {notes.isError ? (
        <p role="alert">Impossible de charger les avoirs.</p>
      ) : (
        notes.data?.map((note) => (
          <article
            key={note.id}
            className="space-y-2 rounded border p-4 text-sm"
          >
            <p className="font-medium">
              {note.reference} · {note.total} € TTC
            </p>
            <p className="break-words">{note.reason}</p>
            <button
              disabled={busy}
              className="underline"
              onClick={async () => {
                setBusy(true);
                try {
                  await download(
                    await billing(`credit-notes/${note.id}/pdf`),
                    `${note.reference}.pdf`,
                  );
                } catch (error) {
                  setMessage((error as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              Télécharger l’avoir PDF
            </button>
            <p>
              Rapprochez séparément les sommes déjà reçues et tout remboursement
              effectivement réalisé. Téléchargez et transmettez ensemble
              l’original et son avoir.
            </p>
          </article>
        ))
      )}
      {canIssue && (
        <form
          className="space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            const form = new FormData(e.currentTarget);
            setBusy(true);
            try {
              if (!key.current) key.current = crypto.randomUUID();
              await billing(`invoices/${invoiceId}/credit-notes`, {
                method: "POST",
                body: JSON.stringify({
                  reason: form.get("reason"),
                  idempotency_key: key.current,
                }),
              });
              setMessage("Avoir total émis. Aucun remboursement exécuté.");
              await cache.invalidateQueries({
                queryKey: ["invoice-credits", workspace, invoiceId],
              });
              onChanged();
            } catch (error) {
              setMessage((error as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <label className="block text-sm">
            Motif de l’avoir total
            <textarea
              name="reason"
              minLength={5}
              maxLength={2000}
              required
              onChange={() => {
                key.current = "";
              }}
              className="mt-2 block w-full rounded border bg-background p-3"
            />
          </label>
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" required className="mt-1" />
            Je confirme la correction intégrale de cette facture. L’avoir émis
            sera conservé et ne sera pas modifiable.
          </label>
          <button
            disabled={busy}
            className="rounded border border-violet-300 px-4 py-2 text-sm text-violet-800"
          >
            Émettre l’avoir total
          </button>
        </form>
      )}
      <div className="space-y-2 border-t pt-4 text-sm">
        <p>
          Facturation électronique : aucun connecteur de plateforme agréée n’est
          encore configuré. Le dossier JSON ci-dessous prépare un échange avec
          un prestataire ; ce n’est pas un format réglementaire validé ni une
          transmission.
        </p>
        <button
          disabled={busy || ["DRAFT", "CANCELLED"].includes(status)}
          className="rounded border px-4 py-2"
          onClick={async () => {
            setBusy(true);
            try {
              await download(
                await billing(`invoices/${invoiceId}/exchange`),
                `invoice-${invoiceId}-exchange.json`,
              );
            } catch (error) {
              setMessage((error as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          Télécharger le dossier pour le prestataire
        </button>
      </div>
      {message && (
        <p role="status" className="text-sm">
          {message}
        </p>
      )}
    </section>
  );
}
