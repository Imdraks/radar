"use client";

import { KanbanBoard } from "@/components/leads";
import { AppLayout, ProtectedRoute } from "@/components/layout";

export default function KanbanPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold">Vue Kanban</h1>
            <p className="text-muted-foreground">
              Gérez vos leads par glisser-déposer
            </p>
          </div>

          <KanbanBoard />
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
