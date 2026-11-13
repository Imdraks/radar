'use client';
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState } from 'react';
import {
  FolderOpen,
  FileText,
  Sheet,
  Calendar,
  ExternalLink,
  Plus,
  Loader2,
  Check,
  AlertCircle,
} from 'lucide-react';
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { toast } from 'sonner';

interface GoogleLinkProps {
  type: 'folder' | 'doc' | 'sheet' | 'calendar';
  entityType: 'client' | 'project' | 'deliverable';
  entityId: number;
  existingId?: string | null;
  existingUrl?: string | null;
  label?: string;
  onCreated?: (id: string, url: string) => void;
  size?: 'sm' | 'default';
}

const icons = {
  folder: FolderOpen,
  doc: FileText,
  sheet: Sheet,
  calendar: Calendar,
};

const labels = {
  folder: 'Dossier Drive',
  doc: 'Brief',
  sheet: 'Report',
  calendar: 'Événement',
};

const colors = {
  folder: 'text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:hover:bg-blue-900/20',
  doc: 'text-blue-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20',
  sheet: 'text-green-600 hover:text-green-700 hover:bg-green-50 dark:hover:bg-green-900/20',
  calendar: 'text-purple-600 hover:text-purple-700 hover:bg-purple-50 dark:hover:bg-purple-900/20',
};

export function GoogleLink({
  type,
  entityType,
  entityId,
  existingId,
  existingUrl,
  label,
  onCreated,
  size = 'default',
}: GoogleLinkProps) {
  const [isCreating, setIsCreating] = useState(false);
  const [localId, setLocalId] = useState(existingId);
  const [localUrl, setLocalUrl] = useState(existingUrl);

  const Icon = icons[type];
  const displayLabel = label || labels[type];
  const colorClass = colors[type];

  const getEndpoint = () => {
    const base = `/api/v1/drive`;
    
    if (type === 'folder') {
      return `${base}/${entityType}s/${entityId}/folder`;
    }
    if (type === 'doc') {
      return `${base}/${entityType}s/${entityId}/brief`;
    }
    if (type === 'sheet') {
      return `${base}/${entityType}s/${entityId}/report`;
    }
    if (type === 'calendar') {
      return `${base}/${entityType}s/${entityId}/deadline-event`;
    }
    return '';
  };

  const handleCreate = async () => {
    setIsCreating(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(getEndpoint(), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (res.status === 401) {
        toast.error('Connexion Google requise', {
          description: 'Veuillez connecter votre compte Google dans les paramètres.',
          action: {
            label: 'Paramètres',
            onClick: () => window.location.href = '/settings?tab=integrations',
          },
        });
        return;
      }

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Erreur de création');
      }

      const data = await res.json();
      setLocalId(data.id);
      setLocalUrl(data.url);
      
      toast.success(`${displayLabel} créé !`);
      
      if (onCreated) {
        onCreated(data.id, data.url);
      }

      // Open in new tab
      if (data.url) {
        window.open(data.url, '_blank');
      }
    } catch (err: any) {
      toast.error(err.message || 'Erreur de création');
    } finally {
      setIsCreating(false);
    }
  };

  const handleOpen = () => {
    if (localUrl) {
      window.open(localUrl, '_blank');
    }
  };

  const hasLink = !!localId;

  if (size === 'sm') {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className={`h-8 px-2 ${colorClass}`}
              onClick={hasLink ? handleOpen : handleCreate}
              disabled={isCreating}
            >
              {isCreating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Icon className="h-4 w-4" />
                  {hasLink && <Check className="h-3 w-3 ml-1" />}
                </>
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            {hasLink ? `Ouvrir ${displayLabel}` : `Créer ${displayLabel}`}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return (
    <Button
      variant={hasLink ? "outline" : "secondary"}
      size="sm"
      className={`gap-2 ${hasLink ? colorClass : ''}`}
      onClick={hasLink ? handleOpen : handleCreate}
      disabled={isCreating}
    >
      {isCreating ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Icon className="h-4 w-4" />
      )}
      {displayLabel}
      {hasLink ? (
        <ExternalLink className="h-3 w-3" />
      ) : (
        <Plus className="h-3 w-3" />
      )}
    </Button>
  );
}

// Wrapper for all Google links in a row
interface GoogleLinksBarProps {
  entityType: 'client' | 'project';
  entityId: number;
  folderId?: string | null;
  briefDocId?: string | null;
  reportSheetId?: string | null;
  calendarEventId?: string | null;
  hasDeadline?: boolean;
  onUpdate?: (field: string, id: string, url: string) => void;
}

export function GoogleLinksBar({
  entityType,
  entityId,
  folderId,
  briefDocId,
  reportSheetId,
  calendarEventId,
  hasDeadline = false,
  onUpdate,
}: GoogleLinksBarProps) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      <GoogleLink
        type="folder"
        entityType={entityType}
        entityId={entityId}
        existingId={folderId}
        size="sm"
        onCreated={(id, url) => onUpdate?.('drive_folder_id', id, url)}
      />
      
      {entityType === 'project' && (
        <>
          <GoogleLink
            type="doc"
            entityType={entityType}
            entityId={entityId}
            existingId={briefDocId}
            size="sm"
            onCreated={(id, url) => onUpdate?.('brief_doc_id', id, url)}
          />
          
          <GoogleLink
            type="sheet"
            entityType={entityType}
            entityId={entityId}
            existingId={reportSheetId}
            size="sm"
            onCreated={(id, url) => onUpdate?.('report_sheet_id', id, url)}
          />
          
          {hasDeadline && (
            <GoogleLink
              type="calendar"
              entityType={entityType}
              entityId={entityId}
              existingId={calendarEventId}
              size="sm"
              onCreated={(id, url) => onUpdate?.('calendar_event_id', id, url)}
            />
          )}
        </>
      )}
    </div>
  );
}

// Status indicator for Google connection
interface GoogleConnectionStatusProps {
  connected: boolean;
  onConnect?: () => void;
}

export function GoogleConnectionStatus({ connected, onConnect }: GoogleConnectionStatusProps) {
  if (connected) {
    return (
      <div className="flex items-center gap-2 text-sm text-green-600">
        <Check className="h-4 w-4" />
        Google connecté
      </div>
    );
  }

  return (
    <Button variant="outline" size="sm" onClick={onConnect} className="gap-2">
      <AlertCircle className="h-4 w-4 text-yellow-500" />
      Connecter Google
    </Button>
  );
}
