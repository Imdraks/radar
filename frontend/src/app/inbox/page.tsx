'use client';
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Inbox,
  Plus,
  Search,
  Filter,
  CheckCircle2,
  ArrowRight,
  Loader2,
  Lightbulb,
  Bug,
  FileText,
  HelpCircle,
  Clock,
  Trash2,
  Archive,
  RefreshCw,
  X,
  Send,
  Tag,
  Calendar,
  User,
  Link as LinkIcon,
  MoreHorizontal,
  FolderOpen,
  DollarSign,
  Package,
} from 'lucide-react';
import Link from 'next/link';
import { AppLayoutWithOnboarding, ProtectedRoute } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { format, formatDistanceToNow } from 'date-fns';
import { fr } from 'date-fns/locale';
import { toast } from 'sonner';

interface InboxItem {
  id: number;
  workspace_id: number;
  created_by: number;
  creator_name?: string;
  text: string;
  link?: string;
  type: string;
  tags: string[];
  status: string;
  due_date?: string;
  mentioned_client?: string;
  mentioned_project?: string;
  triaged_to_type?: string;
  triaged_to_id?: number;
  created_at: string;
  is_overdue: boolean;
  age_hours: number;
}

interface InboxData {
  items: InboxItem[];
  total: number;
  inbox_count: number;
  triaged_count: number;
  done_count: number;
}

const typeIcons: Record<string, any> = {
  idea: Lightbulb,
  request: HelpCircle,
  bug: Bug,
  content: FileText,
  task: CheckCircle2,
  other: Inbox,
};

const typeColors: Record<string, string> = {
  idea: 'text-yellow-500 bg-yellow-50 dark:bg-yellow-900/20',
  request: 'text-blue-500 bg-blue-50 dark:bg-blue-900/20',
  bug: 'text-red-500 bg-red-50 dark:bg-red-900/20',
  content: 'text-purple-500 bg-purple-50 dark:bg-purple-900/20',
  task: 'text-green-500 bg-green-50 dark:bg-green-900/20',
  other: 'text-gray-500 bg-gray-50 dark:bg-neutral-950/20',
};

// Function to render text with colored mentions
const renderColoredText = (text: string) => {
  // Regex patterns for different mention types with custom colors
  const patterns = [
    { regex: /@(\w+)/g, color: '#7adb62' }, // @client = vert
    { regex: /#(\w+)/g, color: '#d69c55' }, // #projet = orange
    { regex: /due:(\S+)/g, color: '#3300f8' }, // due: = bleu
    { regex: /type:(\w+)/g, color: '#c12322' }, // type: = rouge
  ];

  // Split and colorize
  let parts: (string | JSX.Element)[] = [text];
  let keyCounter = 0;

  patterns.forEach(({ regex, color }) => {
    const newParts: (string | JSX.Element)[] = [];
    parts.forEach((part) => {
      if (typeof part === 'string') {
        const splitParts = part.split(regex);
        const matches = part.match(regex) || [];
        let matchIdx = 0;
        splitParts.forEach((sp, i) => {
          if (i % 2 === 0) {
            if (sp) newParts.push(sp);
          } else {
            // This is the captured group (without prefix)
            const fullMatch = matches[matchIdx++] || '';
            newParts.push(
              <span key={`colored-${keyCounter++}`} style={{ color, fontWeight: 500 }}>
                {fullMatch}
              </span>
            );
          }
        });
      } else {
        newParts.push(part);
      }
    });
    parts = newParts;
  });

  return <>{parts}</>;
};

export default function InboxPage() {
  return (
    <ProtectedRoute>
      <AppLayoutWithOnboarding>
        <InboxContent />
      </AppLayoutWithOnboarding>
    </ProtectedRoute>
  );
}

function InboxContent() {
  const [data, setData] = useState<InboxData | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('inbox');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  
  // Quick capture state
  const [captureText, setCaptureText] = useState('');
  const [captureLink, setCaptureLink] = useState('');
  const [isCapturing, setIsCapturing] = useState(false);
  const [showCaptureExpanded, setShowCaptureExpanded] = useState(false);
  const captureInputRef = useRef<HTMLTextAreaElement>(null);
  
  // Mention suggestions
  const [showMentions, setShowMentions] = useState(false);
  const [mentionQuery, setMentionQuery] = useState('');
  const [mentionType, setMentionType] = useState<'@' | '#'>('@');
  const [cursorPosition, setCursorPosition] = useState(0);
  const [clients, setClients] = useState<string[]>([]);
  const [projects, setProjects] = useState<string[]>([]);
  
  // Triage modal
  const [triageItem, setTriageItem] = useState<InboxItem | null>(null);
  const [triageTarget, setTriageTarget] = useState<string>('task');
  const [isTriaging, setIsTriaging] = useState(false);

  // Workspace state
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);

  // Fetch workspace on mount
  useEffect(() => {
    const fetchWorkspace = async () => {
      // First check localStorage
      const storedId = localStorage.getItem('current_workspace_id');
      if (storedId) {
        setWorkspaceId(storedId);
        return;
      }
      
      // If not in localStorage, fetch user's workspaces
      try {
        const token = localStorage.getItem('access_token');
        if (!token) {
          setWorkspaceError('Non authentifié');
          setLoading(false);
          return;
        }
        
        const res = await workspaceFetch('/api/v1/workspaces', {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        
        if (res.ok) {
          const data = await res.json();
          if (data.items && data.items.length > 0) {
            const firstWsId = data.items[0].id.toString();
            localStorage.setItem('current_workspace_id', firstWsId);
            setWorkspaceId(firstWsId);
          } else {
            setWorkspaceError('Aucun workspace disponible');
            setLoading(false);
          }
        } else {
          setWorkspaceError('Erreur de chargement des workspaces');
          setLoading(false);
        }
      } catch (err) {
        console.error('Failed to fetch workspaces', err);
        setWorkspaceError('Erreur de connexion');
        setLoading(false);
      }
    };
    
    fetchWorkspace();
  }, []);

  // Fetch clients and projects for mentions
  useEffect(() => {
    const fetchMentionData = async () => {
      try {
        const token = localStorage.getItem('access_token');
        // Fetch clients (endpoint is /agency/clients)
        const clientsRes = await workspaceFetch('/api/v1/agency/clients?limit=100', {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (clientsRes.ok) {
          const clientsData = await clientsRes.json();
          setClients(clientsData.map((c: any) => c.name));
        }
        // Fetch projects (endpoint is /agency/projects)
        const projectsRes = await workspaceFetch('/api/v1/agency/projects?limit=100', {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (projectsRes.ok) {
          const projectsData = await projectsRes.json();
          setProjects(projectsData.map((p: any) => p.name));
        }
      } catch (err) {
        console.error('Failed to fetch mention data', err);
      }
    };
    fetchMentionData();
  }, []);

  // Handle text changes and detect @ or # triggers
  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value;
    const cursor = e.target.selectionStart;
    setCaptureText(text);
    setCursorPosition(cursor);
    
    // Check for @ or # mention trigger
    const textBeforeCursor = text.slice(0, cursor);
    const lastAtIndex = textBeforeCursor.lastIndexOf('@');
    const lastHashIndex = textBeforeCursor.lastIndexOf('#');
    
    // Determine which trigger is more recent
    if (lastAtIndex > lastHashIndex && lastAtIndex >= 0) {
      const query = textBeforeCursor.slice(lastAtIndex + 1);
      // Only show if no space after @ and query is reasonable
      if (!query.includes(' ') && query.length <= 30) {
        setMentionType('@');
        setMentionQuery(query.toLowerCase());
        setShowMentions(true);
        return;
      }
    } else if (lastHashIndex > lastAtIndex && lastHashIndex >= 0) {
      const query = textBeforeCursor.slice(lastHashIndex + 1);
      if (!query.includes(' ') && query.length <= 30) {
        setMentionType('#');
        setMentionQuery(query.toLowerCase());
        setShowMentions(true);
        return;
      }
    }
    
    setShowMentions(false);
  };

  // Insert selected mention
  const insertMention = (value: string) => {
    const textBeforeCursor = captureText.slice(0, cursorPosition);
    const textAfterCursor = captureText.slice(cursorPosition);
    
    // Find the trigger position
    const triggerChar = mentionType;
    const triggerIndex = textBeforeCursor.lastIndexOf(triggerChar);
    
    if (triggerIndex >= 0) {
      const newText = textBeforeCursor.slice(0, triggerIndex) + triggerChar + value + ' ' + textAfterCursor;
      setCaptureText(newText);
      setShowMentions(false);
      
      // Focus back to textarea
      setTimeout(() => {
        if (captureInputRef.current) {
          captureInputRef.current.focus();
          const newCursor = triggerIndex + triggerChar.length + value.length + 1;
          captureInputRef.current.setSelectionRange(newCursor, newCursor);
        }
      }, 0);
    }
  };

  // Create new client via API
  const createClient = async (name: string) => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch('/api/v1/agency/clients', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, type: 'artist' }),
      });
      if (res.ok) {
        const newClient = await res.json();
        setClients(prev => [...prev, newClient.name]);
        toast.success(`Client "${name}" créé !`);
        return newClient.name;
      }
    } catch (err) {
      toast.error('Erreur création client');
    }
    return null;
  };

  // Create new project via API
  const createProject = async (name: string) => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch('/api/v1/agency/projects', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, status: 'active' }),
      });
      if (res.ok) {
        const newProject = await res.json();
        setProjects(prev => [...prev, newProject.name]);
        toast.success(`Projet "${name}" créé !`);
        return newProject.name;
      }
    } catch (err) {
      toast.error('Erreur création projet');
    }
    return null;
  };

  // Handle creating and inserting a new mention
  const handleCreateMention = async (name: string) => {
    let createdName: string | null = null;
    if (mentionType === '@') {
      createdName = await createClient(name);
    } else {
      createdName = await createProject(name);
    }
    if (createdName) {
      insertMention(createdName);
    }
  };

  // Get filtered suggestions (with "create new" option)
  const getMentionSuggestions = () => {
    const items = mentionType === '@' ? clients : projects;
    if (!mentionQuery) return { existing: items.slice(0, 5), canCreate: false, createName: '' };
    const filtered = items.filter(item => 
      item.toLowerCase().includes(mentionQuery)
    ).slice(0, 5);
    // Check if exact match exists
    const exactMatch = items.some(item => item.toLowerCase() === mentionQuery.toLowerCase());
    return { 
      existing: filtered, 
      canCreate: !exactMatch && mentionQuery.length >= 2,
      createName: mentionQuery.charAt(0).toUpperCase() + mentionQuery.slice(1)
    };
  };

  const fetchInbox = useCallback(async () => {
    if (!workspaceId) return;
    
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const params = new URLSearchParams({
        workspace_id: workspaceId,
        limit: '100',
      });
      
      if (statusFilter && statusFilter !== 'all') {
        params.set('status_filter', statusFilter);
      }
      if (typeFilter && typeFilter !== 'all') {
        params.set('type_filter', typeFilter);
      }
      
      const res = await workspaceFetch(`/api/v1/inbox?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      if (!res.ok) throw new Error('Failed to fetch inbox');
      const result = await res.json();
      setData(result);
    } catch (err) {
      console.error(err);
      toast.error('Erreur de chargement');
    } finally {
      setLoading(false);
    }
  }, [workspaceId, statusFilter, typeFilter]);

  useEffect(() => {
    if (workspaceId) {
      fetchInbox();
    }
  }, [fetchInbox, workspaceId]);

  // Quick capture submit
  const handleCapture = async () => {
    if (!captureText.trim()) return;
    
    setIsCapturing(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/inbox?workspace_id=${workspaceId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: captureText,
          link: captureLink || undefined,
        }),
      });
      
      if (!res.ok) throw new Error('Failed to create');
      
      setCaptureText('');
      setCaptureLink('');
      setShowCaptureExpanded(false);
      toast.success('Capturé !');
      fetchInbox();
    } catch (err) {
      toast.error('Erreur de capture');
    } finally {
      setIsCapturing(false);
    }
  };

  // Keyboard shortcut for capture
  const handleCaptureKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleCapture();
    }
  };

  // Triage submit
  const handleTriage = async () => {
    if (!triageItem) return;
    
    setIsTriaging(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await workspaceFetch(`/api/v1/inbox/${triageItem.id}/triage`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          target: triageTarget,
          task_title: triageItem.text.slice(0, 200),
        }),
      });
      
      if (!res.ok) throw new Error('Failed to triage');
      
      const result = await res.json();
      toast.success(result.message);
      setTriageItem(null);
      fetchInbox();
    } catch (err) {
      toast.error('Erreur de triage');
    } finally {
      setIsTriaging(false);
    }
  };

  // Quick actions
  const handleMarkDone = async (item: InboxItem) => {
    try {
      const token = localStorage.getItem('access_token');
      await workspaceFetch(`/api/v1/inbox/${item.id}/done`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      toast.success('Marqué comme fait');
      fetchInbox();
    } catch (err) {
      toast.error('Erreur');
    }
  };

  const handleArchive = async (item: InboxItem) => {
    try {
      const token = localStorage.getItem('access_token');
      await workspaceFetch(`/api/v1/inbox/${item.id}/archive`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      toast.success('Archivé');
      fetchInbox();
    } catch (err) {
      toast.error('Erreur');
    }
  };

  const handleDelete = async (item: InboxItem) => {
    if (!confirm('Supprimer cet élément ?')) return;
    
    try {
      const token = localStorage.getItem('access_token');
      await workspaceFetch(`/api/v1/inbox/${item.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      toast.success('Supprimé');
      fetchInbox();
    } catch (err) {
      toast.error('Erreur');
    }
  };

  // Show error if no workspace
  if (workspaceError) {
    return (
      <div className="p-6 max-w-5xl mx-auto">
        <Card className="border-orange-200 bg-orange-50 dark:bg-orange-950/20">
          <CardContent className="pt-6">
            <div className="text-center space-y-6">
              <Inbox className="h-12 w-12 mx-auto text-orange-500" />
              <div className="space-y-2">
                <h2 className="text-xl font-semibold text-orange-800 dark:text-orange-200">
                  {workspaceError}
                </h2>
                <p className="text-orange-600 dark:text-orange-300">
                  Veuillez créer un workspace pour utiliser l'inbox.
                </p>
              </div>
              <Link href="/workspaces">
                <Button>Gérer les Workspaces</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Show loading if workspace not yet determined
  if (!workspaceId) {
    return (
      <div className="p-6 max-w-5xl mx-auto flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Inbox className="h-6 w-6" />
            Inbox
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Capture rapide d'idées, demandes et tâches
          </p>
        </div>
        <Button onClick={fetchInbox} variant="ghost" size="sm">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Quick Capture */}
      <Card className="border-2 border-dashed border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/20">
        <CardContent className="pt-4">
          <div className="space-y-3 relative">
            <Textarea
              ref={captureInputRef}
              placeholder="Capturer une idée... (ex: @client #projet due:2026-02-01 type:idee)"
              value={captureText}
              onChange={handleTextChange}
              onKeyDown={handleCaptureKeyDown}
              onFocus={() => setShowCaptureExpanded(true)}
              onBlur={() => setTimeout(() => setShowMentions(false), 200)}
              className="min-h-[60px] resize-none border-0 bg-transparent focus-visible:ring-0 text-lg !text-gray-900 dark:!text-white placeholder:text-gray-400"
            />
            
            {/* Mention Suggestions Dropdown */}
            {showMentions && (getMentionSuggestions().existing.length > 0 || getMentionSuggestions().canCreate) && (
              <div className="absolute top-16 left-0 z-50 w-64 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1">
                <div className="px-3 py-1 text-xs font-medium text-gray-500 border-b border-gray-100 dark:border-gray-700">
                  {mentionType === '@' ? 'Clients' : 'Projets'}
                </div>
                {getMentionSuggestions().existing.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => insertMention(item)}
                    className="w-full px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 flex items-center gap-2 transition-colors"
                  >
                    <span style={{ color: mentionType === '@' ? '#7adb62' : '#d69c55', fontWeight: 500 }}>
                      {mentionType}{item}
                    </span>
                  </button>
                ))}
                {/* Create new option */}
                {getMentionSuggestions().canCreate && (
                  <button
                    onClick={() => handleCreateMention(getMentionSuggestions().createName)}
                    className="w-full px-3 py-2 text-left hover:bg-green-50 dark:hover:bg-green-900/20 text-green-600 dark:text-green-400 flex items-center gap-2 transition-colors border-t border-gray-100 dark:border-gray-700"
                  >
                    <Plus className="h-4 w-4" />
                    <span>Créer "{getMentionSuggestions().createName}"</span>
                  </button>
                )}
              </div>
            )}
            
            {showCaptureExpanded && (
              <div className="flex items-center gap-3 pt-2 border-t border-blue-200 dark:border-blue-800">
                <div className="flex-1 flex items-center gap-2">
                  <LinkIcon className="h-4 w-4 text-gray-400" />
                  <Input
                    placeholder="Lien (optionnel)"
                    value={captureLink}
                    onChange={(e) => setCaptureLink(e.target.value)}
                    className="h-8 text-sm"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setShowCaptureExpanded(false);
                      setCaptureText('');
                      setCaptureLink('');
                    }}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleCapture}
                    disabled={!captureText.trim() || isCapturing}
                  >
                    {isCapturing ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        <Send className="h-4 w-4 mr-1" />
                        Capturer
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}
            
            {!showCaptureExpanded && (
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <Tag className="h-3 w-3" />
                <span style={{ color: '#7adb62' }}>@client</span>
                <span style={{ color: '#d69c55' }}>#projet</span>
                <Calendar className="h-3 w-3 ml-2" />
                <span style={{ color: '#3300f8' }}>due:YYYY-MM-DD</span>
                <span style={{ color: '#c12322' }}>type:idee</span>
                <span className="ml-auto">⌘+Enter pour capturer</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
          {[
            { value: 'inbox', label: 'Inbox', count: data?.inbox_count },
            { value: 'triaged', label: 'Triés', count: data?.triaged_count },
            { value: 'done', label: 'Faits', count: data?.done_count },
            { value: 'all', label: 'Tous' },
          ].map((tab) => (
            <button
              key={tab.value}
              onClick={() => setStatusFilter(tab.value)}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                statusFilter === tab.value
                  ? 'bg-white dark:bg-gray-700 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              {tab.label}
              {tab.count !== undefined && (
                <span className="ml-1 text-xs text-gray-400">({tab.count})</span>
              )}
            </button>
          ))}
        </div>
        
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-[140px]">
            <Filter className="h-4 w-4 mr-2" />
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous types</SelectItem>
            <SelectItem value="idea">Idée</SelectItem>
            <SelectItem value="request">Demande</SelectItem>
            <SelectItem value="bug">Bug</SelectItem>
            <SelectItem value="content">Contenu</SelectItem>
            <SelectItem value="task">Tâche</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Items List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : data?.items.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Inbox className="h-12 w-12 text-gray-300 dark:text-gray-600 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              Inbox vide
            </h3>
            <p className="text-gray-500 text-center max-w-md">
              Capturez vos idées, demandes et tâches ici. Utilisez @client #projet pour tagger.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {data?.items.map((item) => {
            const TypeIcon = typeIcons[item.type] || Inbox;
            const typeColor = typeColors[item.type] || typeColors.other;
            
            return (
              <Card key={item.id} className={`group hover:shadow-md transition-shadow ${
                item.status === 'triaged' ? 'opacity-70' : ''
              }`}>
                <CardContent className="p-4">
                  <div className="flex items-start gap-4">
                    {/* Type Icon */}
                    <div className={`p-2 rounded-lg ${typeColor}`}>
                      <TypeIcon className="h-4 w-4" />
                    </div>
                    
                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <p className="text-gray-900 dark:text-white">
                        {renderColoredText(item.text)}
                      </p>
                      
                      <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDistanceToNow(new Date(item.created_at), { addSuffix: true, locale: fr })}
                        </span>
                        
                        {item.mentioned_client && (
                          <span className="flex items-center gap-1" style={{ color: '#7adb62' }}>
                            <User className="h-3 w-3" />
                            @{item.mentioned_client}
                          </span>
                        )}
                        
                        {item.tags && item.tags.length > 0 && (
                          <span className="flex items-center gap-1" style={{ color: '#d69c55' }}>
                            <Tag className="h-3 w-3" />
                            {item.tags.map(t => `#${t}`).join(' ')}
                          </span>
                        )}
                        
                        {item.due_date && (
                          <span className={`flex items-center gap-1 ${item.is_overdue ? 'text-red-500' : ''}`}>
                            <Calendar className="h-3 w-3" />
                            {format(new Date(item.due_date), 'd MMM', { locale: fr })}
                          </span>
                        )}
                        
                        {item.link && (
                          <a href={item.link} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline flex items-center gap-1">
                            <LinkIcon className="h-3 w-3" />
                            Lien
                          </a>
                        )}
                      </div>
                      
                      {/* Triaged info */}
                      {item.status === 'triaged' && item.triaged_to_type && (
                        <div className="mt-2">
                          <Badge variant="secondary" className="text-xs">
                            Trié → {item.triaged_to_type}
                          </Badge>
                        </div>
                      )}
                    </div>
                    
                    {/* Actions - Dropdown Menu */}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {item.status === 'inbox' && (
                          <>
                            <DropdownMenuItem onClick={() => setTriageItem(item)}>
                              <ArrowRight className="h-4 w-4 mr-2" />
                              Trier vers...
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleMarkDone(item)} className="text-green-600">
                              <CheckCircle2 className="h-4 w-4 mr-2" />
                              Marquer fait
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                          </>
                        )}
                        <DropdownMenuItem onClick={() => handleArchive(item)}>
                          <Archive className="h-4 w-4 mr-2" />
                          Archiver
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleDelete(item)} className="text-red-600">
                          <Trash2 className="h-4 w-4 mr-2" />
                          Supprimer
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Triage Modal */}
      <Dialog open={!!triageItem} onOpenChange={(open) => !open && setTriageItem(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Trier vers...</DialogTitle>
            <DialogDescription>
              Convertir cet élément en action concrète
            </DialogDescription>
          </DialogHeader>
          
          {triageItem && (
            <div className="space-y-4 py-4">
              <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg text-sm">
                {triageItem.text}
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                {[
                  { value: 'task', label: 'Tâche', desc: 'Action à faire', icon: CheckCircle2 },
                  { value: 'deal', label: 'Deal', desc: 'Opportunité commerciale', icon: DollarSign },
                  { value: 'project', label: 'Projet', desc: 'Nouveau projet', icon: FolderOpen },
                  { value: 'deliverable', label: 'Livrable', desc: 'À livrer', icon: Package },
                ].map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setTriageTarget(option.value)}
                    className={`p-4 rounded-lg border-2 text-left transition-colors ${
                      triageTarget === option.value
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <p className="font-medium flex items-center gap-1.5">{(() => { const Icon = option.icon; return <Icon className="h-4 w-4" />; })()}{option.label}</p>
                    <p className="text-xs text-gray-500">{option.desc}</p>
                  </button>
                ))}
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setTriageItem(null)}>
              Annuler
            </Button>
            <Button onClick={handleTriage} disabled={isTriaging}>
              {isTriaging ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Trier'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
