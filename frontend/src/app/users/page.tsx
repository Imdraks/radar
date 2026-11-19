"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import {
  Plus,
  MoreVertical,
  Pencil,
  Trash,
  Shield,
  User as UserIcon,
  Users as UsersIcon,
} from "lucide-react";
import { AdminLayout, ProtectedRoute } from "@/components/layout";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { usersApi } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import type { User } from "@/lib/types";

const ROLE_CONFIG: Record<string, { color: string; label: string }> = {
  admin: { color: "bg-red-100 text-red-800", label: "Admin" },
  bizdev: { color: "bg-blue-100 text-blue-800", label: "BizDev" },
  pm: { color: "bg-purple-100 text-purple-800", label: "PM" },
  viewer: { color: "bg-gray-100 text-gray-800", label: "Viewer" },
};

function UsersContent() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);

  const { data: users, isLoading } = useQuery<User[]>({
    queryKey: ["users"],
    queryFn: () => usersApi.getAll(),
  });

  const createMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => usersApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setDialogOpen(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
      usersApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setDialogOpen(false);
      setEditingUser(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => usersApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
  });

  const handleSubmit = (data: Record<string, unknown>) => {
    if (editingUser) {
      // Remove password if empty
      if (!data.password) {
        delete data.password;
      }
      updateMutation.mutate({ id: editingUser.id, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const handleEdit = (user: User) => {
    setEditingUser(user);
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingUser(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Utilisateurs</h1>
          <p className="text-muted-foreground">
            Gérez les accès à la plateforme
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) setEditingUser(null);
        }}>
          <DialogTrigger asChild>
            <Button onClick={() => { setEditingUser(null); setDialogOpen(true); }}>
              <Plus className="h-4 w-4 mr-2" />
              Nouvel utilisateur
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {editingUser ? "Modifier l'utilisateur" : "Nouvel utilisateur"}
              </DialogTitle>
            </DialogHeader>
            <UserForm
              user={editingUser}
              onSubmit={handleSubmit}
              isLoading={createMutation.isPending || updateMutation.isPending}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Users list */}
      {isLoading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto" />
        </div>
      ) : users?.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          Aucun utilisateur
        </div>
      ) : (
        <div className="grid gap-4">
          {users?.map((user) => {
            const roleConfig = ROLE_CONFIG[user.role] || ROLE_CONFIG.viewer;
            const hasGoogle = user.linked_accounts?.some(acc => acc.provider === 'google');
            const hasApple = user.linked_accounts?.some(acc => acc.provider === 'apple');
            return (
              <Card key={user.id}>
                <CardContent className="p-4">
                  <div className="flex items-center gap-4">
                    {user.avatar_url ? (
                      <img 
                        src={user.avatar_url} 
                        alt={user.full_name || user.email}
                        className="w-12 h-12 rounded-full object-cover"
                      />
                    ) : (
                      <div className="w-12 h-12 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-lg font-medium">
                        {user.full_name?.charAt(0) || user.email.charAt(0).toUpperCase()}
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold">
                          {user.full_name || user.email}
                        </h3>
                        <Badge className={roleConfig.color}>{roleConfig.label}</Badge>
                        {user.is_superuser && (
                          <Badge variant="outline">
                            <Shield className="h-3 w-3 mr-1" />
                            Super Admin
                          </Badge>
                        )}
                        {!user.is_active && (
                          <Badge variant="secondary">Inactif</Badge>
                        )}
                        {/* SSO Provider badges */}
                        {hasGoogle && (
                          <Badge variant="outline" className="bg-white border-gray-300">
                            <svg className="h-3 w-3 mr-1" viewBox="0 0 24 24">
                              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                            </svg>
                            Google
                          </Badge>
                        )}
                        {hasApple && (
                          <Badge variant="outline" className="bg-black text-white border-black">
                            <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/>
                            </svg>
                            Apple
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">{user.email}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Créé le {formatDateTime(user.created_at)}
                      </p>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => handleEdit(user)}>
                          <Pencil className="h-4 w-4 mr-2" />
                          Modifier
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={() => deleteMutation.mutate(user.id)}
                        >
                          <Trash className="h-4 w-4 mr-2" />
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
    </div>
  );
}

function UserForm({
  user,
  onSubmit,
  isLoading,
}: {
  user: User | null;
  onSubmit: (data: Record<string, unknown>) => void;
  isLoading: boolean;
}) {
  const { register, handleSubmit, watch, setValue } = useForm<{
    email: string;
    password?: string;
    full_name: string;
    role: string;
    is_active: boolean;
    is_collaborator: boolean;
  }>({
    defaultValues: user ? {
      email: user.email,
      password: "",
      full_name: user.full_name || "",
      role: user.role,
      is_active: user.is_active,
      is_collaborator: user.is_collaborator || false,
    } : {
      email: "",
      password: "",
      full_name: "",
      role: "viewer",
      is_active: true,
      is_collaborator: false,
    },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          {...register("email", { required: true })}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">
          {user ? "Nouveau mot de passe (laisser vide pour conserver)" : "Mot de passe"}
        </Label>
        <Input
          id="password"
          type="password"
          {...register("password", { required: !user })}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="full_name">Nom complet</Label>
        <Input id="full_name" {...register("full_name")} />
      </div>

      <div className="space-y-2">
        <Label htmlFor="role">Rôle</Label>
        <Select value={watch("role")} onValueChange={(v) => setValue("role", v)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="admin">Admin</SelectItem>
            <SelectItem value="bizdev">BizDev</SelectItem>
            <SelectItem value="pm">PM</SelectItem>
            <SelectItem value="viewer">Viewer</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center gap-2">
        <Switch
          id="is_active"
          checked={watch("is_active")}
          onCheckedChange={(v) => setValue("is_active", v)}
        />
        <Label htmlFor="is_active">Utilisateur actif</Label>
      </div>

      <div className="space-y-2 rounded-xl border p-4">
        <div className="flex items-center gap-2"><Switch id="is_collaborator" checked={watch("is_collaborator")} onCheckedChange={value => setValue("is_collaborator", value)} /><Label htmlFor="is_collaborator">Compte collaborateur</Label></div>
        <p className="text-xs leading-6 text-muted-foreground">Demander le choix du workspace après chaque connexion. Ce mode n’ajoute aucun droit ni accès à une entreprise.</p>
      </div>
      <DialogFooter>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? "Enregistrement..." : user ? "Modifier" : "Créer"}
        </Button>
      </DialogFooter>
    </form>
  );
}

export default function UsersPage() {
  return (
    <ProtectedRoute requiredRoles={["admin"]}>
      <AdminLayout>
        <UsersContent />
      </AdminLayout>
    </ProtectedRoute>
  );
}
