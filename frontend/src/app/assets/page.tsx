'use client';

import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { Folder } from 'lucide-react';
import { AppLayoutWithOnboarding, ProtectedRoute } from "@/components/layout";
import { AssetsList } from "@/components/assets";
import api from '@/lib/api';

export default function AssetsPage() {
  return (
    <ProtectedRoute>
      <AppLayoutWithOnboarding>
        <AssetsContent />
      </AppLayoutWithOnboarding>
    </ProtectedRoute>
  );
}

function AssetsContent() {
  const router = useRouter();
  
  // Fetch projects for filter dropdown
  const { data: projects = [] } = useQuery({
    queryKey: ['projects-list'],
    queryFn: async () => {
      const response = await api.get('/agency/projects');
      return response.data?.map((p: any) => ({ id: p.id, name: p.name })) || [];
    },
  });
  
  const handleViewProject = (projectId: number) => {
    router.push(`/projects/${projectId}?tab=assets`);
  };
  
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-purple-100 rounded-lg">
            <Folder className="h-6 w-6 text-purple-600" />
          </div>
          <h1 className="text-[28px] font-semibold tracking-tight text-foreground">Bibliothèque d'assets</h1>
        </div>
        <p className="text-gray-500">
          Tous vos assets centralisés : maquettes, documents, liens, médias...
        </p>
      </div>
      
      {/* Assets list with all filters */}
      <AssetsList
        showProjectFilter={true}
        showProjectColumn={true}
        projects={projects}
        onViewProject={handleViewProject}
      />
    </div>
  );
}
