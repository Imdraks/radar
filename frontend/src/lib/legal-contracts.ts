export const documentLabels: Record<string, string> = {
  sales_terms: "Conditions générales de vente B2B",
  dpa: "Accord de sous-traitance",
  retention: "Conservation des données",
  reversibility: "Réversibilité",
  security: "Mesures de sécurité",
  subprocessors: "Prestataires et transferts",
};
export interface LegalBundle {
  id: number;
  version: string;
  content_hash: string;
  publisher: Record<string, string>;
  documents: Record<string, string>;
  published_at: string;
}
export async function legalFetch(path: string, init?: RequestInit) {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const response = await fetch(`/api/v1/legal-contracts/${path}`, {
    ...init,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      "Content-Type": "application/json",
      ...init?.headers,
    },
    cache: "no-store",
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Service contractuel indisponible",
    );
  }
  return response.json();
}
