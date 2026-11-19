'use client';

import { useRef, useState } from 'react';
import { ImagePlus, Loader2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AccountPhoto } from '@/components/landing/PublicAccount';
import { useAuthStore } from '@/store/auth';
import { api } from '@/lib/api';

export function ProfilePhotoSettings() {
  const user = useAuthStore(state => state.user);
  const setUser = useAuthStore(state => state.setUser);
  const input = useRef<HTMLInputElement>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const custom = user?.avatar_url?.startsWith('data:image/jpeg;base64,');
  const change = async (file?: File) => {
    setError(''); setMessage('');
    if (file && (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 2 * 1024 * 1024)) {
      setError('Choisissez un fichier JPEG, PNG ou WebP de 2 Mo maximum.');
      return;
    }
    setPending(true);
    try {
      const body = new FormData();
      if (file) body.append('file', file);
      const response = file
        ? await api.post('/auth/me/avatar', body, { headers: { 'Content-Type': 'multipart/form-data' } })
        : await api.delete('/auth/me/avatar');
      setUser(response.data);
      setMessage(file ? 'Votre photo a été mise à jour.' : 'Photo personnalisée retirée. Votre photo de connexion est utilisée si elle est disponible.');
    } catch (failure: unknown) {
      const detail = (failure as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Impossible de modifier la photo. Réessayez.');
    } finally {
      setPending(false);
      if (input.current) input.current.value = '';
    }
  };
  if (!user) return null;
  return <Card><CardHeader><CardTitle className="text-lg">Photo de profil</CardTitle><CardDescription>Votre photo Google est utilisée par défaut lorsqu’elle est disponible. Vous pouvez choisir votre propre image.</CardDescription></CardHeader><CardContent>
    <div className="flex flex-wrap items-center gap-5"><AccountPhoto user={user} className="h-16 w-16" /><div className="space-y-3"><div className="flex flex-wrap gap-2"><Button variant="outline" disabled={pending} onClick={() => input.current?.click()} className="gap-2">{pending ? <Loader2 size={16} className="animate-spin" /> : <ImagePlus size={16} />}Choisir une photo</Button>{custom && <Button variant="ghost" disabled={pending} onClick={() => void change()}>Retirer la photo personnalisée</Button>}</div><p id="profile-photo-help" className="text-xs text-muted-foreground">JPEG, PNG ou WebP · 2 Mo et 4 millions de pixels maximum · Recadrage carré automatique</p></div></div>
    <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" aria-label="Photo de profil à importer" aria-describedby="profile-photo-help" className="sr-only" tabIndex={-1} disabled={pending} onChange={event => { const file = event.target.files?.[0]; event.target.value = ''; if (file) void change(file); }} />
    {error && <p role="alert" className="mt-4 text-sm text-destructive">{error}</p>}{message && <p role="status" className="mt-4 text-sm text-muted-foreground">{message}</p>}
  </CardContent></Card>;
}
