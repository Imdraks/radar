"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { opportunitiesApi } from "@/lib/api";
import { formatCurrency, formatRelativeDate, getScoreColor } from "@/lib/utils";
import { Opportunity } from "@/lib/types";
import {
  Calendar,
  Euro,
  Building2,
  GripVertical,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";

const COLUMNS = [
  { id: "new", title: "📥 Nouveau", color: "bg-blue-500" },
  { id: "review", title: "👀 En revue", color: "bg-yellow-500" },
  { id: "contacted", title: "📞 Contacté", color: "bg-purple-500" },
  { id: "proposal", title: "📝 Proposition", color: "bg-orange-500" },
  { id: "won", title: "🏆 Gagné", color: "bg-green-500" },
  { id: "lost", title: "❌ Perdu", color: "bg-red-500" },
];

interface KanbanCardProps {
  opportunity: Opportunity;
  isDragging?: boolean;
}

function KanbanCard({ opportunity, isDragging }: KanbanCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: opportunity.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="bg-card border rounded-lg p-3 mb-2 cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow"
    >
      <div className="flex items-start gap-2">
        <button
          {...attributes}
          {...listeners}
          className="mt-1 text-muted-foreground hover:text-foreground"
        >
          <GripVertical className="h-4 w-4" />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1">
            <Link
              href={`/leads/${opportunity.id}`}
              className="font-medium text-sm truncate hover:underline flex items-center gap-1"
            >
              {opportunity.title}
              <ExternalLink className="h-3 w-3" />
            </Link>
            <Badge className={`${getScoreColor(opportunity.score)} text-white text-xs`}>
              {opportunity.score}
            </Badge>
          </div>
          
          {opportunity.organization_name && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
              <Building2 className="h-3 w-3" />
              <span className="truncate">{opportunity.organization_name}</span>
            </div>
          )}
          
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            {opportunity.budget_amount && (
              <div className="flex items-center gap-1">
                <Euro className="h-3 w-3" />
                <span>{formatCurrency(opportunity.budget_amount)}</span>
              </div>
            )}
            {opportunity.deadline_at && (
              <div className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                <span>{formatRelativeDate(opportunity.deadline_at)}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

interface KanbanColumnProps {
  column: typeof COLUMNS[0];
  opportunities: Opportunity[];
}

function KanbanColumn({ column, opportunities }: KanbanColumnProps) {
  return (
    <div className="flex-shrink-0 w-72">
      <Card className="h-full">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium flex items-center justify-between">
            <span>{column.title}</span>
            <Badge variant="secondary" className="ml-2">
              {opportunities.length}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-2">
          <ScrollArea className="h-[calc(100vh-280px)]">
            <SortableContext
              items={opportunities.map((o) => o.id)}
              strategy={verticalListSortingStrategy}
            >
              {opportunities.map((opportunity) => (
                <KanbanCard key={opportunity.id} opportunity={opportunity} />
              ))}
            </SortableContext>
            {opportunities.length === 0 && (
              <div className="text-center py-8 text-muted-foreground text-sm">
                Aucune opportunité
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}

export function KanbanBoard() {
  const queryClient = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const { data, isLoading } = useQuery({
    queryKey: ["opportunities", "kanban"],
    queryFn: () => opportunitiesApi.getAll({ limit: 200 }),
  });

  // Extract items from paginated response
  const opportunities = data?.items || [];

  const updateStatusMutation = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      return opportunitiesApi.update(id, { status });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["opportunities"] });
    },
  });

  const getOpportunitiesByStatus = (status: string) => {
    return opportunities.filter((o: Opportunity) => o.status === status);
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over) return;

    const activeOpp = opportunities.find((o: Opportunity) => String(o.id) === String(active.id));
    if (!activeOpp) return;

    // Determine which column was dropped on
    const overId = over.id as string;
    let newStatus = overId;

    // If dropped on an opportunity, get its status
    const overOpp = opportunities.find((o: Opportunity) => String(o.id) === overId);
    if (overOpp) {
      newStatus = overOpp.status;
    }

    // Check if it's a valid column
    const validColumn = COLUMNS.find((c) => c.id === newStatus);
    if (!validColumn) return;

    if (activeOpp.status !== newStatus) {
      updateStatusMutation.mutate({ id: String(activeOpp.id), status: newStatus });
    }
  };

  const activeOpportunity = activeId
    ? opportunities.find((o: Opportunity) => String(o.id) === String(activeId))
    : null;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 overflow-x-auto pb-4">
        {COLUMNS.map((column) => (
          <KanbanColumn
            key={column.id}
            column={column}
            opportunities={getOpportunitiesByStatus(column.id)}
          />
        ))}
      </div>

      <DragOverlay>
        {activeOpportunity ? (
          <div className="w-72">
            <KanbanCard opportunity={activeOpportunity} isDragging />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
