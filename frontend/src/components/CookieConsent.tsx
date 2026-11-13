"use client";

import { useState, useEffect } from "react";
import Script from "next/script";

type ConsentChoice = "granted" | "denied";

interface ConsentState {
  analytics: ConsentChoice;
  marketing: ConsentChoice;
}

function updateGTMConsent(consent: ConsentState) {
  if (typeof window !== "undefined" && window.gtag) {
    window.gtag("consent", "update", {
      analytics_storage: consent.analytics,
      ad_storage: consent.marketing,
      ad_user_data: consent.marketing,
      ad_personalization: consent.marketing,
    });
  }
}

export default function CookieConsent() {
  const [visible, setVisible] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [analytics, setAnalytics] = useState(false);
  const [consent, setConsent] = useState<ConsentState | null>(null);
  const [marketing, setMarketing] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("cookie-consent");
    if (!saved) {
      setVisible(true);
    } else {
      try {
        const consent: ConsentState = JSON.parse(saved);
        if (!["granted", "denied"].includes(consent.analytics) || !["granted", "denied"].includes(consent.marketing)) throw new Error("Invalid consent");
        setConsent(consent);
        updateGTMConsent(consent);
      } catch {
        setVisible(true);
      }
    }
  }, []);

  const saveConsent = (consent: ConsentState) => {
    const previouslyGranted = localStorage.getItem("cookie-consent")?.includes("granted");
    localStorage.setItem("cookie-consent", JSON.stringify(consent));
    setConsent(consent);
    if (previouslyGranted && consent.analytics === "denied") {
      for (const cookie of document.cookie.split(";")) {
        const name = cookie.split("=")[0].trim();
        if (/^(_ga|_gid|_gat)/.test(name)) {
          const labels = window.location.hostname.split(".");
          const domains = ["", window.location.hostname, ...labels.slice(0,-1).map((_,i) => "." + labels.slice(i).join("."))];
          for (const domain of domains) {
            document.cookie = `${name}=; Max-Age=0; path=/` + (domain ? `; domain=${domain}` : "");
          }
        }
      }
      updateGTMConsent(consent);
      window.location.reload();
      return;
    }
    updateGTMConsent(consent);
    setVisible(false);
  };

  const acceptAll = () => {
    saveConsent({ analytics: "granted", marketing: "granted" });
  };

  const rejectAll = () => {
    saveConsent({ analytics: "denied", marketing: "denied" });
  };

  const saveCustom = () => {
    saveConsent({
      analytics: analytics ? "granted" : "denied",
      marketing: marketing ? "granted" : "denied",
    });
  };

  if (!visible) return <>
    <ConsentAnalytics consent={consent} />
    <button type="button" onClick={() => { setAnalytics(consent?.analytics === "granted"); setMarketing(consent?.marketing === "granted"); setVisible(true); }} className="fixed bottom-2 right-3 z-50 rounded bg-white px-2 py-1 text-xs text-slate-600 shadow-sm">Préférences cookies</button>
  </>;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-[9999] p-4 sm:p-6">
      <div className="mx-auto max-w-2xl rounded-2xl border border-zinc-200 bg-white p-6 shadow-2xl dark:border-zinc-700 dark:bg-zinc-900">
        <div className="flex items-start gap-3">
          <svg className="h-6 w-6 mt-0.5 text-amber-500 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"/><path d="M8.5 8.5v.01"/><path d="M16 15.5v.01"/><path d="M12 12v.01"/><path d="M11 17v.01"/><path d="M7 14v.01"/></svg>
          <div className="flex-1">
            <h3 className="text-base font-semibold text-zinc-900 dark:text-white">
              Respect de votre vie privée
            </h3>
            <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
              Nous utilisons des cookies pour analyser le trafic et améliorer
              votre expérience. Les cookies essentiels sont toujours actifs.
              Vous pouvez choisir d&apos;accepter ou non les cookies
              optionnels.
            </p>

            {showDetails && (
              <div className="mt-4 space-y-3 rounded-lg bg-zinc-50 p-4 dark:bg-zinc-800">
                <label className="flex items-center gap-3 cursor-not-allowed">
                  <input
                    type="checkbox"
                    checked
                    disabled
                    className="h-4 w-4 rounded accent-blue-600"
                  />
                  <div>
                    <span className="text-sm font-medium text-zinc-900 dark:text-white">
                      Essentiels
                    </span>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400">
                      Nécessaires au fonctionnement du site (session,
                      sécurité).
                    </p>
                  </div>
                </label>

                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={analytics}
                    onChange={(e) => setAnalytics(e.target.checked)}
                    className="h-4 w-4 rounded accent-blue-600"
                  />
                  <div>
                    <span className="text-sm font-medium text-zinc-900 dark:text-white">
                      Analytiques
                    </span>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400">
                      Google Analytics — mesure de fréquentation anonyme.
                    </p>
                  </div>
                </label>

                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={marketing}
                    onChange={(e) => setMarketing(e.target.checked)}
                    className="h-4 w-4 rounded accent-blue-600"
                  />
                  <div>
                    <span className="text-sm font-medium text-zinc-900 dark:text-white">
                      Marketing
                    </span>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400">
                      Cookies publicitaires et de personnalisation.
                    </p>
                  </div>
                </label>
              </div>
            )}

            <div className="mt-4 flex flex-wrap items-center gap-2">
              <button
                onClick={acceptAll}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
              >
                Tout accepter
              </button>
              <button
                onClick={rejectAll}
                className="rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 transition-colors dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700"
              >
                Tout refuser
              </button>
              {showDetails ? (
                <button
                  onClick={saveCustom}
                  className="rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 transition-colors dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700"
                >
                  Enregistrer mes choix
                </button>
              ) : (
                <button
                  onClick={() => setShowDetails(true)}
                  className="px-4 py-2 text-sm font-medium text-zinc-500 hover:text-zinc-700 transition-colors dark:text-zinc-400 dark:hover:text-zinc-200"
                >
                  Personnaliser
                </button>
              )}
            </div>

            <p className="mt-3 text-xs text-zinc-400 dark:text-zinc-500">
              En savoir plus dans notre{" "}
              <a
                href="/privacy"
                className="underline hover:text-zinc-600 dark:hover:text-zinc-300"
              >
                politique de confidentialité
              </a>
              .
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// No third-party request occurs until an explicit choice. No GTM container can load extra tags.
function ConsentAnalytics({consent}: {consent: ConsentState | null}) {
  const id = process.env.NEXT_PUBLIC_GA_ID;
  if (consent?.analytics !== "granted" || !id || !/^G-[A-Z0-9]+$/.test(id)) return null;
  return <>
    <Script id="radar-consent-config" strategy="afterInteractive">{`
      window.dataLayer = window.dataLayer || [];
      window.gtag = function(){window.dataLayer.push(arguments)};
      window.gtag('consent','default',{analytics_storage:'granted',ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied'});
      window.gtag('js', new Date());
      window.gtag('config', '${id}', {allow_google_signals:false,allow_ad_personalization_signals:false});
    `}</Script>
    <Script src={`https://www.googletagmanager.com/gtag/js?id=${id}`} strategy="afterInteractive" />
  </>;
}
