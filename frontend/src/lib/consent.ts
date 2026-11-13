export const CONSENT_VERSION = "2026-11-13";
export type ConsentState = { version: typeof CONSENT_VERSION; chosenAt: string; analytics: "granted" | "denied" };
export function consentExpiresAt(chosenAt: string): number {
  const date = new Date(chosenAt); const day = date.getUTCDate();
  date.setUTCDate(1); date.setUTCMonth(date.getUTCMonth() + 6);
  const last = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0)).getUTCDate();
  date.setUTCDate(Math.min(day, last)); return date.getTime();
}
export function readConsent(raw: string | null, now = Date.now()): ConsentState | null {
  try {
    if (!raw) return null;
    const value = JSON.parse(raw);
    if (value.version !== CONSENT_VERSION || !["granted", "denied"].includes(value.analytics) || typeof value.chosenAt !== "string") return null;
    const chosen = Date.parse(value.chosenAt);
    if (!Number.isFinite(chosen) || chosen > now + 60000 || consentExpiresAt(value.chosenAt) <= now) return null;
    return { version: CONSENT_VERSION, chosenAt: value.chosenAt, analytics: value.analytics };
  } catch { return null; }
}
