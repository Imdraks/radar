"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { LegalDocument, LegalSection } from "@/components/legal/LegalDocument";
import {
  legalFetch,
  documentLabels,
  type LegalBundle,
} from "@/lib/legal-contracts";
function Content() {
  const params = useSearchParams();
  const version = params.get("version");
  const [bundle, setBundle] = useState<LegalBundle | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setBundle(null);
    setError("");
    legalFetch(
      version && /^\d+$/.test(version) ? `versions/${version}` : "current",
    )
      .then((data) => {
        if (active) {
          if (!data?.documents || !data.version)
            throw new Error("Aucun dossier contractuel publié");
          setBundle(data);
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [version]);
  return (
    <LegalDocument title="Documents contractuels publiés">
      {error ? (
        <p role="status">
          {error}. Les pages de présentation ne remplacent pas un contrat
          validé.
        </p>
      ) : !bundle ? (
        <p>Chargement…</p>
      ) : (
        <>
          <p>
            Version {bundle.version} · éditeur : {bundle.publisher.name}. Cette
            consultation ne vaut pas acceptation ni paiement.
          </p>
          <p className="break-all text-xs">
            Empreinte SHA-256 : {bundle.content_hash}
          </p>
          <button
            className="rounded border px-4 py-2"
            onClick={() => {
              const url = URL.createObjectURL(
                new Blob([JSON.stringify(bundle, null, 2)], {
                  type: "application/json",
                }),
              );
              const a = document.createElement("a");
              a.href = url;
              a.download = `radar-contracts-${bundle.version}.json`;
              a.click();
              URL.revokeObjectURL(url);
            }}
          >
            Télécharger cette version
          </button>
          {Object.entries(bundle.documents).map(([key, text]) => (
            <LegalSection key={key} id={key} title={documentLabels[key] || key}>
              <div className="whitespace-pre-wrap break-words">{text}</div>
            </LegalSection>
          ))}
        </>
      )}
    </LegalDocument>
  );
}
export default function Page() {
  return (
    <Suspense fallback={<p>Chargement…</p>}>
      <Content />
    </Suspense>
  );
}
