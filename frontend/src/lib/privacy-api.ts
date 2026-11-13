export async function privacyFetch(path:string,init?:RequestInit) {
 const token=localStorage.getItem('access_token');
 const response=await fetch(`/api/v1/privacy/${path}`,{...init,headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json',...init?.headers},cache:'no-store'});
 if (!response.ok) {let detail='La demande n’a pas pu être traitée.';try{const data=await response.json();if(typeof data.detail==='string')detail=data.detail;}catch{}throw new Error(detail);}
 return response;
}
export const rightsLabels:Record<string,string>={access:'Accès',rectification:'Rectification',erasure:'Effacement',portability:'Portabilité',objection:'Opposition',restriction:'Limitation',cancellation:'Résiliation',switching:'Réversibilité'};
export const requestStatus:Record<string,string>={received:'Reçue',in_progress:'En cours',answered:'Réponse disponible',refused:'Refus motivé'};
export interface RightsRequest {id:number;workspace_id:number|null;kind:string;scope:string;status:string;details:string;created_at:string;response_due_at:string;response:string|null;}
