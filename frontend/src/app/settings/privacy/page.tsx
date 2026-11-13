'use client';
import {useState} from 'react';
import Link from 'next/link';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {AppLayout,ProtectedRoute} from '@/components/layout';
import {useAuthStore} from '@/store/auth';
import {privacyFetch,rightsLabels,requestStatus,type RightsRequest} from '@/lib/privacy-api';
function Content(){
 const user=useAuthStore(s=>s.user);const cache=useQueryClient();const [busy,setBusy]=useState(false);const [message,setMessage]=useState('');
 const {data,isLoading,isError}=useQuery<RightsRequest[]>({queryKey:['privacy-requests',user?.id],queryFn:async()=> (await privacyFetch('requests')).json(),enabled:!!user});
 return <div className="mx-auto max-w-4xl space-y-7"><h1 className="text-3xl font-semibold">Données et droits</h1>
 <p className="text-sm leading-7 text-muted-foreground">Déposez une demande concernant vos données ou, si vous administrez un workspace, sa résiliation ou sa réversibilité. Le dépôt est enregistré ; il ne supprime pas automatiquement les comptes, documents ou factures. Les droits restent accessibles indépendamment de l’abonnement.</p>
 <div className="flex flex-wrap gap-4"><Link className="text-violet-700 underline" href="/privacy">Politique de confidentialité</Link><Link className="text-violet-700 underline" href="/reversibility">Périmètre de réversibilité</Link>{user?.is_superuser&&<Link className="underline" href="/admin/privacy-requests">Traiter les demandes de droits</Link>}</div>
 <button type="button" disabled={busy} className="rounded-lg border bg-card px-4 py-2" onClick={async()=>{setBusy(true);try{const response=await privacyFetch('account-export');const url=URL.createObjectURL(await response.blob());const link=document.createElement('a');link.href=url;link.download='radar-account.json';link.click();URL.revokeObjectURL(url);}catch(e){setMessage((e as Error).message);}finally{setBusy(false);}}}>Exporter mes données de compte (JSON)</button>
 <p className="text-xs text-muted-foreground">Export partiel : identité du compte et ses demandes. Il ne contient ni mots de passe ni données des autres membres et ne remplace pas un export complet du workspace.</p>
 <form className="space-y-4 rounded-2xl border bg-card p-6" onSubmit={async e=>{e.preventDefault();const element=e.currentTarget;const form=new FormData(element);setBusy(true);setMessage('');try{const kind=String(form.get('kind'));const workspace=kind==='switching'||kind==='cancellation'||form.get('scope')==='workspace';const selected=localStorage.getItem('current_workspace_id');const suffix=workspace&&selected?`?workspace_id=${encodeURIComponent(selected)}`:'';const result=await (await privacyFetch('requests'+suffix,{method:'POST',body:JSON.stringify({kind,scope:workspace?'workspace':'personal',details:form.get('details')||''})})).json();setMessage(`Demande n°${result.id} enregistrée. Vous pourrez consulter ici la réponse de l’opérateur.`);element.reset();await cache.invalidateQueries({queryKey:['privacy-requests',user?.id]});}catch(error){setMessage((error as Error).message);}finally{setBusy(false);}}}>
 <h2 className="text-lg font-semibold">Nouvelle demande</h2>
 <div className="text-sm"><label htmlFor="rights-kind">Objet</label><select id="rights-kind" name="kind" className="mt-2 block w-full rounded-lg border bg-background p-3">{Object.entries(rightsLabels).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></div>
 <div className="text-sm"><label htmlFor="rights-scope">Périmètre</label><select id="rights-scope" name="scope" className="mt-2 block w-full rounded-lg border bg-background p-3"><option value="personal">Mes données personnelles</option><option value="workspace">Workspace administré</option></select></div>
 <label className="block text-sm">Précisions facultatives<textarea name="details" maxLength={3000} rows={4} className="mt-2 block w-full rounded-lg border bg-background p-3" aria-describedby="rights-data-warning"/></label>
 <p id="rights-data-warning" className="text-xs text-muted-foreground">Ne joignez ni pièce d’identité, ni mot de passe, ni secret d’intégration. Une vérification proportionnée ne sera demandée qu’en cas de doute raisonnable.</p>
 <button disabled={busy} className="rounded-lg bg-violet-700 px-4 py-2 text-white disabled:opacity-50">Enregistrer la demande</button>
 </form>
 {message&&<p role="status" className="rounded-lg border p-3 text-sm">{message}</p>}
 <section className="space-y-4"><h2 className="text-lg font-semibold">Mes demandes</h2>{isLoading?<p>Chargement…</p>:isError?<p role="alert">Impossible de charger vos demandes.</p>:!data?.length?<p>Aucune demande enregistrée.</p>:data.map(row=><article key={row.id} className="space-y-2 rounded-xl border bg-card p-5"><h3 className="font-medium">N°{row.id} · {rightsLabels[row.kind]||row.kind} · {requestStatus[row.status]||row.status}</h3><p className="text-xs text-muted-foreground">Reçue le {new Date(row.created_at+'Z').toLocaleDateString('fr-FR')} · échéance de suivi : {new Date(row.response_due_at+'Z').toLocaleDateString('fr-FR')}</p><p className="whitespace-pre-wrap text-sm">{row.details}</p>{row.response&&<p className="whitespace-pre-wrap rounded-lg bg-violet-50 p-3 text-sm text-violet-950">{row.response}</p>}</article>)}</section>
 </div>;
}
export default function Page(){return <ProtectedRoute><AppLayout><Content/></AppLayout></ProtectedRoute>;}
