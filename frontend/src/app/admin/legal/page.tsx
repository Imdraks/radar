"use client";
import { useState } from "react";
import Link from "next/link";
import { AdminLayout, ProtectedRoute } from "@/components/layout";
import { useAuthStore } from "@/store/auth";
import { legalFetch } from "@/lib/legal-contracts";
function Content() {
  const user = useAuthStore((s) => s.user);
  const [value, setValue] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  if (!user?.is_superuser) return <p>Accès réservé à la plateforme.</p>;
  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <h1 className="text-2xl font-semibold">Publication contractuelle</h1>
      <p>
        Publiez uniquement un dossier complet relu et autorisé, contenant les
        informations réelles de l’éditeur, de l’hébergement et des prestataires.
        Les textes publiés sont accessibles au public et immuables. Ne collez
        aucun secret ou donnée client.
      </p>
      <Link className="underline" href="/contracts">
        Consulter les documents publiés
      </Link>
      <form
        className="space-y-4"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            const body = JSON.parse(value);
            const result = await legalFetch("admin/publish", {
              method: "POST",
              body: JSON.stringify(body),
            });
            setMessage(
              `Version ${result.version} publiée, empreinte ${result.content_hash}. Aucune acceptation client ni activation n’a été créée.`,
            );
          } catch (error) {
            setMessage((error as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label className="block">
          Dossier JSON validé
          <textarea
            required
            rows={16}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className="mt-2 block w-full rounded border bg-background p-3 font-mono text-xs"
          />
        </label>
        <p className="text-sm">
          Le dossier doit inclure les six textes, l’identité, une version
          unique, une référence de revue et la déclaration explicite
          reviewed_for_publication. Un modèle non complété est refusé.
        </p>
        <button
          disabled={busy}
          className="rounded bg-violet-700 px-4 py-2 text-white"
        >
          Publier cette version validée
        </button>
      </form>
      {message && (
        <p role="status" className="break-words">
          {message}
        </p>
      )}
    </div>
  );
}
export default function Page() {
  return (
    <ProtectedRoute>
      <AdminLayout>
        <Content />
      </AdminLayout>
    </ProtectedRoute>
  );
}
