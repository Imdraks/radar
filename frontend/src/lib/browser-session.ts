import {
  isBrowserToken, deviceProofHeaders,
  devicePublicKey,
  tokenSessionId,
} from "./device-proof";
/** Persistent browser storage contains only a marker, never a reusable JWT. */
export const COOKIE_SESSION = "cookie-session";
export async function storeBrowserSession(access: string, refresh: string) {
  if (isBrowserToken(access) && isBrowserToken(refresh)) return;
  const sid = tokenSessionId(access);
  const proof = sid
    ? await deviceProofHeaders(
        "POST",
        (process.env.NEXT_PUBLIC_API_URL ?? "") +
          "/api/v1/auth/browser/session",
        sid,
      )
    : {};
  const response = await fetch(
    (process.env.NEXT_PUBLIC_API_URL ?? "") + "/api/v1/auth/browser/session",
    {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${access}`,
        ...proof,
      },
      body: JSON.stringify({
        refresh_token: refresh,
        public_key: await devicePublicKey(),
      }),
    },
  );
  if (!response.ok)
    throw new Error(
      "La session sécurisée n’a pas pu être établie. Reconnectez-vous.",
    );
  const body = await response.json();
  if (body.session_id || sid)
    localStorage.setItem("radar_browser_session", body.session_id || sid);
  localStorage.setItem("access_token", COOKIE_SESSION + ((body.session_id || sid) ? "." + (body.session_id || sid) : ""));
  localStorage.setItem("refresh_token", COOKIE_SESSION + ((body.session_id || sid) ? "." + (body.session_id || sid) : ""));
}

export { isBrowserToken } from "./device-proof";
