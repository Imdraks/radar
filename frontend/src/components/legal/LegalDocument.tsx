import Link from 'next/link';
import { RadarLogo } from '@/components/brand/RadarBrand';
import legal from '@/config/legal.json';
export function LegalDocument({title,children}:{title:string;children:React.ReactNode}) {
 return <main className="radar-public min-h-screen bg-slate-50 px-5 py-10 text-slate-800"><div className="mx-auto max-w-4xl">
  <Link href="/" aria-label="Radar — Accueil" className="block w-fit"><RadarLogo/></Link>
  <nav aria-label="Documents juridiques" className="my-7 flex flex-wrap gap-x-5 gap-y-3 text-sm text-violet-700">{[['/legal','Mentions légales'],['/privacy','Confidentialité'],['/terms','CGU'],['/sales-terms','Conditions commerciales'],['/cookies','Cookies'],['/data-processing','Sous-traitance'],['/subprocessors','Prestataires'],['/reversibility','Réversibilité'],['/accessibility','Accessibilité']].map(([url,label])=><Link key={url} href={url} className="underline underline-offset-4">{label}</Link>)}</nav>
  <h1 className="text-3xl font-semibold tracking-tight">{title}</h1><p className="mt-3 text-sm text-slate-600">Version du {legal.noticeVersion} · Service destiné aux professionnels</p>
  {!legal.commercialReleaseEnabled && <p role="status" className="my-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">Version de validation. L’identité de l’éditeur, les conditions commerciales, les durées de conservation et les prestataires de production doivent être complétés avant ouverture commerciale. Ces pages ne constituent pas une certification de conformité.</p>}
  <div className="my-8 space-y-7 rounded-2xl border bg-white p-6 text-sm leading-7 sm:p-9">{children}</div>
 </div></main>;
}
export function LegalSection({id,title,children}:{id?:string;title:string;children:React.ReactNode}) {return <section id={id} className="scroll-mt-6"><h2 className="mb-2 text-lg font-semibold text-slate-950">{title}</h2>{children}</section>;}
export function PrivacyContact(){const email=legal.privacyContact||legal.contactEmail;return email?<a className="underline text-violet-700" href={`mailto:${email}`}>{email}</a>:<span>Contact de l’éditeur à renseigner avant ouverture commerciale</span>;}
export function ContractLink({url,label}:{url:string;label:string}){return url?<a href={url} className="underline text-violet-700">{label}</a>:<span>{label} : document de production non publié</span>;}
