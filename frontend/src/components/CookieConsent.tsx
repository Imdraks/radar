"use client";
import { useEffect,useState } from "react";
import Script from "next/script";
import Link from "next/link";
import legal from "@/config/legal.json";
import {CONSENT_VERSION,readConsent,type ConsentState} from "@/lib/consent";

function clearAnalyticsCookies() {
  const labels=location.hostname.split(".");
  const domains=["",location.hostname,...labels.slice(0,-1).map((_,i)=>"."+labels.slice(i).join("."))];
  for (const cookie of document.cookie.split(";")) {
    const name=cookie.split("=")[0].trim();
    if (/^(_ga|_gid|_gat)/.test(name)) for (const domain of domains) document.cookie=`${name}=; Max-Age=0; path=/`+(domain?`; domain=${domain}`:"");
  }
}
export default function CookieConsent() {
  const [consent,setConsent]=useState<ConsentState|null>(null);
  const [visible,setVisible]=useState(false);
  const [details,setDetails]=useState(false);
  const [analytics,setAnalytics]=useState(false);
  useEffect(()=>{
    let saved:ConsentState|null=null;
    try {saved=readConsent(localStorage.getItem("cookie-consent"));} catch {/* Storage blocked: no analytics. */}
    setConsent(saved);setAnalytics(saved?.analytics==="granted");setVisible(!saved);
    if (!saved) clearAnalyticsCookies();
  },[]);
  const save=(granted:boolean)=>{
    const previous=consent?.analytics==="granted";
    const value:ConsentState={version:CONSENT_VERSION,chosenAt:new Date().toISOString(),analytics:granted?"granted":"denied"};
    try {localStorage.setItem("cookie-consent",JSON.stringify(value));} catch {/* Choice applies only to this page. */}
    setConsent(value);setVisible(false);
    if (!granted) {
      window.gtag?.("consent","update",{analytics_storage:"denied",ad_storage:"denied",ad_user_data:"denied",ad_personalization:"denied"});
      clearAnalyticsCookies();
      if (previous) location.reload();
    }
  };
  if (!visible) return <>
    <ConsentAnalytics consent={consent}/>
    <button type="button" onClick={()=>{setAnalytics(consent?.analytics==="granted");setVisible(true);}} className="fixed bottom-2 right-3 z-50 rounded bg-white px-2 py-1 text-xs text-slate-700 shadow-sm">Préférences cookies</button>
  </>;
  const choiceClass="rounded-lg border border-violet-200 bg-white px-4 py-2 text-sm font-medium text-violet-900 hover:bg-violet-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-600";
  return <aside aria-label="Choix des cookies" className="fixed bottom-0 left-0 right-0 z-[9999] p-4">
    <div className="mx-auto max-w-2xl rounded-2xl border bg-white p-5 text-slate-900 shadow-xl">
      <h2 className="font-semibold">Respect de votre vie privée</h2>
      <p className="mt-2 text-sm leading-relaxed">Le fonctionnement et la sécurité utilisent des stockages nécessaires. Avec votre accord uniquement, Google Analytics peut mesurer l’audience si ce service est activé. Refuser ne limite pas l’accès. Le choix est conservé six mois et peut être retiré à tout moment.</p>
      <p className="mt-2 text-xs">Éditeur : {legal.companyName || "identité à renseigner avant ouverture commerciale"}. Prestataire de mesure, si activé : Google. Aucune publicité personnalisée n’est activée par ce choix.</p>
      {details && <label className="mt-3 flex items-start gap-3 rounded-lg bg-violet-50 p-3 text-sm"><input type="checkbox" checked={analytics} onChange={e=>setAnalytics(e.target.checked)} className="mt-1"/><span>Mesure d’audience Google Analytics. Les données peuvent être pseudonymes ; elles ne sont pas présentées comme anonymes.</span></label>}
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" onClick={()=>save(false)} className={choiceClass}>Tout refuser</button>
        <button type="button" onClick={()=>save(true)} className={choiceClass}>Tout accepter</button>
        <button type="button" onClick={()=>details?save(analytics):setDetails(true)} className={choiceClass}>{details?"Enregistrer mes choix":"Personnaliser"}</button>
      </div>
      <p className="mt-3 text-xs"><Link className="underline" href="/cookies">Cookies et durées</Link> · <Link className="underline" href="/privacy">Confidentialité et destinataires</Link></p>
    </div>
  </aside>;
}
function ConsentAnalytics({consent}:{consent:ConsentState|null}) {
  const id=process.env.NEXT_PUBLIC_GA_ID;
  if (consent?.analytics!=="granted" || !id || !/^G-[A-Z0-9]+$/.test(id)) return null;
  return <>
    <Script id="radar-consent-config" strategy="afterInteractive">{`window.dataLayer=window.dataLayer||[];window.gtag=function(){window.dataLayer.push(arguments)};window.gtag('consent','default',{analytics_storage:'granted',ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied'});window.gtag('js',new Date());window.gtag('config','${id}',{allow_google_signals:false,allow_ad_personalization_signals:false,cookie_expires:15552000,cookie_update:false});`}</Script>
    <Script src={`https://www.googletagmanager.com/gtag/js?id=${id}`} strategy="afterInteractive"/>
  </>;
}
