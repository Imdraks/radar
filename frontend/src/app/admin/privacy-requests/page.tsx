'use client';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {useState} from 'react';
import {ProtectedRoute,AdminLayout} from '@/components/layout';
import {useAuthStore} from '@/store/auth';
import {privacyFetch,rightsLabels,requestStatus,type RightsRequest} from '@/lib/privacy-api';
function Content(){
 const user=useAuthStore(s=>s.user);const cache=useQueryClient();const [message,setMessage]=useState('');const [busy,setBusy]=useState(false);
 const {data,isError,isLoading}=useQuery<(RightsRequest&{user_id:number})[]>({queryKey:['privacy-admin',user?.id],queryFn:async()=>(await privacyFetch('admin/requests')).json(),enabled:user?.is_superuser===true});
 if(!user?.is_superuser)return <p>Accès réservé à l’opérateur de plateforme.</p>;
 return <div className="space-y-6"><h1 className="text-2xl font-semibold">Demandes de droits et de réversibilité</h1><p className="text-sm">Examinez la base juridique, le périmètre, les délais et les obligations de conservation. Une réponse enregistrée sera consultable dans le compte ; aucun email, transfert ou effacement n’est exécuté automatiquement. Une éventuelle prolongation doit être motivée et notifiée dans le délai légal applicable.</p>{message&&<p role="status">{message}</p>}
 {isLoading?<p>Chargement…</p>:isError?<p role="alert">Demandes indisponibles.</p>:!data?.length?<p>Aucune demande.</p>:data.map(row=><article className="space-y-3 rounded-xl border bg-card p-5" key={row.id}><h2 className="font-semibold">N°{row.id} · {rightsLabels[row.kind]} · utilisateur {row.user_id} · espace {row.workspace_id||'personnel'}</h2><p className="text-sm">{requestStatus[row.status]} · échéance de suivi {new Date(row.response_due_at+'Z').toLocaleDateString('fr-FR')}</p><p className="whitespace-pre-wrap text-sm">{row.details}</p>{row.response&&<p className="whitespace-pre-wrap text-sm">{row.response}</p>}{!['answered','refused'].includes(row.status)&&<form className="space-y-3" onSubmit={async e=>{e.preventDefault();const f=new FormData(e.currentTarget);setBusy(true);try{await privacyFetch(`admin/requests/${row.id}/respond`,{method:'POST',body:JSON.stringify({status:f.get('status'),response:f.get('response'),reference:f.get('reference')})});setMessage('Réponse et trace opérateur enregistrées.');await cache.invalidateQueries({queryKey:['privacy-admin',user?.id]});}catch(error){setMessage((error as Error).message);}finally{setBusy(false);}}}>
 <div className="text-sm"><label htmlFor={`rights-status-${row.id}`}>Statut</label><select id={`rights-status-${row.id}`} name="status" className="block w-full rounded border bg-background p-2"><option value="in_progress">En cours</option><option value="answered">Réponse disponible</option><option value="refused">Refus motivé</option></select></div>
 <label className="block text-sm">Réponse visible par le demandeur<textarea required minLength={10} maxLength={5000} name="response" className="block w-full rounded border bg-background p-2"/></label>
 <label className="block text-sm">Référence interne de traitement<input required minLength={3} maxLength={150} name="reference" className="block w-full rounded border bg-background p-2"/></label>
 <button disabled={busy} className="rounded bg-violet-700 px-4 py-2 text-white">Enregistrer la réponse</button></form>}</article>)}
 </div>;
}
export default function Page(){return <ProtectedRoute><AdminLayout><Content/></AdminLayout></ProtectedRoute>;}
