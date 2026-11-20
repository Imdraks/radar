export function isBrowserToken(token: string | null | undefined){return !!token && (token === "cookie-session" || token.startsWith("cookie-session."));}
/** Non-exportable origin key; protects copied cookies, not a compromised OS/profile. */
const DB = "radar-device-proof-v1";
let pending: Promise<CryptoKeyPair> | undefined;
async function deviceKeys(): Promise<CryptoKeyPair> {
  if (pending) return pending;
  pending = (async () => {
    if (!globalThis.crypto?.subtle)
      throw new Error("Un navigateur sécurisé avec HTTPS est requis.");
    const db = await new Promise<IDBDatabase>((resolve, reject) => {
      const r = indexedDB.open(DB, 1);
      r.onupgradeneeded = () => r.result.createObjectStore("keys");
      r.onsuccess = () => resolve(r.result);
      r.onerror = () =>
        reject(new Error("Stockage sécurisé du navigateur indisponible."));
    });
    const read = () =>
      new Promise<CryptoKeyPair | undefined>((resolve, reject) => {
        const r = db.transaction("keys").objectStore("keys").get("origin");
        r.onsuccess = () => resolve(r.result);
        r.onerror = () => reject(r.error);
      });
    try {
      const existing = await read();
      if (existing) return existing;
      const generated = await crypto.subtle.generateKey(
        { name: "ECDSA", namedCurve: "P-256" },
        false,
        ["sign", "verify"],
      );
      try {
        await new Promise<void>((resolve, reject) => {
          const tx = db.transaction("keys", "readwrite");
          tx.objectStore("keys").add(generated, "origin");
          tx.oncomplete = () => resolve();
          tx.onerror = () => reject(tx.error);
          tx.onabort = () => reject(tx.error);
        });
        return generated;
      } catch {
        const raced = await read();
        if (raced) return raced;
        throw new Error("La clé du navigateur ne peut pas être conservée.");
      }
    } finally {
      db.close();
    }
  })().catch((error) => {
    pending = undefined;
    throw error;
  });
  return pending;
}
export async function devicePublicKey() {
  return crypto.subtle.exportKey("jwk", (await deviceKeys()).publicKey);
}
export function tokenSessionId(token: string): string | undefined {
  try {
    const part = token.split(".")[1];
    return JSON.parse(atob(part.replace(/-/g, "+").replace(/_/g, "/"))).sid;
  } catch {
    return undefined;
  }
}
export async function deviceProofHeaders(
  method: string,
  url: string,
  sid?: string,
): Promise<Record<string, string>> {
  const session = sid || localStorage.getItem("radar_browser_session");
  if (!session) return {};
  const target = new URL(url, window.location.origin);
  const nonce = Array.from(crypto.getRandomValues(new Uint8Array(16)))
    .map((x) => x.toString(16).padStart(2, "0"))
    .join("");
  const issued = String(Math.floor(Date.now() / 1000));
  const message = [
    session,
    method.toUpperCase(),
    target.pathname + target.search,
    issued,
    nonce,
  ].join("\n");
  const signature = new Uint8Array(
    await crypto.subtle.sign(
      { name: "ECDSA", hash: "SHA-256" },
      (await deviceKeys()).privateKey,
      new TextEncoder().encode(message),
    ),
  );
  const encoded = btoa(String.fromCharCode(...Array.from(signature)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  return {
    "X-Radar-Session": session,
    "X-Radar-Issued": issued,
    "X-Radar-Nonce": nonce,
    "X-Radar-Proof": encoded,
  };
}
export function installDeviceFetch() {
  if (typeof window === "undefined") return;
  const guard = window as Window & { __radarDeviceFetch?: boolean };
  if (guard.__radarDeviceFetch) return;
  guard.__radarDeviceFetch = true;
  const original = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    const url = new URL(
      input instanceof Request ? input.url : String(input),
      location.origin,
    );
    const configured = new URL(
      process.env.NEXT_PUBLIC_API_URL || location.origin,
      location.origin,
    ).origin;
    const headers = new Headers(
      init?.headers || (input instanceof Request ? input.headers : undefined),
    );
    if (
      url.origin === configured &&
      url.pathname.startsWith("/api/") &&
      isBrowserToken(localStorage.getItem("access_token")) &&
      !headers.has("X-Radar-Proof")
    ) {
      const proof = await deviceProofHeaders(
        init?.method || (input instanceof Request ? input.method : "GET"),
        url.href,
      );
      Object.entries(proof).forEach(([key, value]) => headers.set(key, value));
    }
    return original(input, {
      ...init,
      headers,
      credentials: url.origin === configured ? "include" : init?.credentials,
    });
  };
}
installDeviceFetch();
