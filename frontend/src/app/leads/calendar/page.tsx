"use client";

import { DeadlinesCalendar } from "@/components/leads";
import { AppLayout, ProtectedRoute } from "@/components/layout";

export default function CalendarPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold">Calendrier des Deadlines</h1>
            <p className="text-muted-foreground">
              Visualisez toutes les échéances à venir
            </p>
          </div>

          <DeadlinesCalendar />
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
