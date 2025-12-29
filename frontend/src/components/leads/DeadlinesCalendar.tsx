"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  format,
  startOfMonth,
  endOfMonth,
  eachDayOfInterval,
  isSameMonth,
  isSameDay,
  isToday,
  addMonths,
  subMonths,
  parseISO,
} from "date-fns";
import { fr } from "date-fns/locale";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { opportunitiesApi } from "@/lib/api";
import { Opportunity } from "@/lib/types";
import { formatCurrency, getScoreColor } from "@/lib/utils";
import {
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
  Euro,
  Building2,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";

interface CalendarDayProps {
  date: Date;
  opportunities: Opportunity[];
  isCurrentMonth: boolean;
  onDayClick: (date: Date, opportunities: Opportunity[]) => void;
}

function CalendarDay({
  date,
  opportunities,
  isCurrentMonth,
  onDayClick,
}: CalendarDayProps) {
  const hasDeadlines = opportunities.length > 0;
  const isCurrentDay = isToday(date);
  const urgentCount = opportunities.filter((o) => (o.score ?? 0) >= 10).length;

  return (
    <button
      onClick={() => hasDeadlines && onDayClick(date, opportunities)}
      disabled={!hasDeadlines}
      className={`
        min-h-[100px] p-2 border border-border rounded-lg text-left transition-colors
        ${!isCurrentMonth ? "bg-muted/30 text-muted-foreground" : "bg-card hover:bg-accent"}
        ${isCurrentDay ? "ring-2 ring-primary" : ""}
        ${hasDeadlines ? "cursor-pointer" : "cursor-default"}
      `}
    >
      <div className="flex items-center justify-between mb-1">
        <span
          className={`text-sm font-medium ${
            isCurrentDay
              ? "bg-primary text-primary-foreground rounded-full w-6 h-6 flex items-center justify-center"
              : ""
          }`}
        >
          {format(date, "d")}
        </span>
        {hasDeadlines && (
          <Badge
            variant={urgentCount > 0 ? "destructive" : "secondary"}
            className="text-xs"
          >
            {opportunities.length}
          </Badge>
        )}
      </div>
      
      {hasDeadlines && (
        <div className="space-y-1">
          {opportunities.slice(0, 3).map((opp) => (
            <div
              key={opp.id}
              className={`text-xs p-1 rounded truncate ${getScoreColor(opp.score)} text-white`}
            >
              {opp.title}
            </div>
          ))}
          {opportunities.length > 3 && (
            <div className="text-xs text-muted-foreground">
              +{opportunities.length - 3} autres
            </div>
          )}
        </div>
      )}
    </button>
  );
}

export function DeadlinesCalendar() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDay, setSelectedDay] = useState<{
    date: Date;
    opportunities: Opportunity[];
  } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["opportunities", "calendar"],
    queryFn: () => opportunitiesApi.getAll({ limit: 500 }),
  });

  // Extract items from paginated response
  const opportunities = data?.items || [];

  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(currentDate);
  const days = eachDayOfInterval({ start: monthStart, end: monthEnd });

  // Add days from previous and next month to fill the grid
  const startWeekday = monthStart.getDay();
  const endWeekday = monthEnd.getDay();
  
  const paddedDays = useMemo(() => {
    const result = [...days];
    // Add previous month days
    for (let i = startWeekday - 1; i >= 0; i--) {
      result.unshift(new Date(monthStart.getFullYear(), monthStart.getMonth(), -i));
    }
    // Add next month days
    for (let i = 1; i < 7 - endWeekday; i++) {
      result.push(new Date(monthEnd.getFullYear(), monthEnd.getMonth() + 1, i));
    }
    return result;
  }, [days, startWeekday, endWeekday, monthStart, monthEnd]);

  const opportunitiesByDate = useMemo(() => {
    const map = new Map<string, Opportunity[]>();
    
    opportunities.forEach((opp: Opportunity) => {
      if (opp.deadline_at) {
        const dateKey = format(parseISO(opp.deadline_at), "yyyy-MM-dd");
        const existing = map.get(dateKey) || [];
        map.set(dateKey, [...existing, opp]);
      }
    });
    
    return map;
  }, [opportunities]);

  const getOpportunitiesForDate = (date: Date) => {
    const dateKey = format(date, "yyyy-MM-dd");
    return opportunitiesByDate.get(dateKey) || [];
  };

  const handleDayClick = (date: Date, opportunities: Opportunity[]) => {
    setSelectedDay({ date, opportunities });
  };

  const goToPreviousMonth = () => setCurrentDate(subMonths(currentDate, 1));
  const goToNextMonth = () => setCurrentDate(addMonths(currentDate, 1));
  const goToToday = () => setCurrentDate(new Date());

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <CalendarIcon className="h-5 w-5" />
              Calendrier des Deadlines
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={goToToday}>
                Aujourd'hui
              </Button>
              <Button variant="outline" size="icon" onClick={goToPreviousMonth}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="font-medium min-w-[150px] text-center">
                {format(currentDate, "MMMM yyyy", { locale: fr })}
              </span>
              <Button variant="outline" size="icon" onClick={goToNextMonth}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Weekday headers */}
          <div className="grid grid-cols-7 gap-2 mb-2">
            {["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"].map((day) => (
              <div
                key={day}
                className="text-center text-sm font-medium text-muted-foreground py-2"
              >
                {day}
              </div>
            ))}
          </div>

          {/* Calendar grid */}
          <div className="grid grid-cols-7 gap-2">
            {paddedDays.map((date, index) => (
              <CalendarDay
                key={index}
                date={date}
                opportunities={getOpportunitiesForDate(date)}
                isCurrentMonth={isSameMonth(date, currentDate)}
                onDayClick={handleDayClick}
              />
            ))}
          </div>

          {/* Legend */}
          <div className="flex items-center gap-4 mt-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-green-500"></div>
              <span>Score élevé (≥10)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-yellow-500"></div>
              <span>Score moyen (5-9)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-gray-500"></div>
              <span>Score faible (&lt;5)</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Day detail dialog */}
      <Dialog open={!!selectedDay} onOpenChange={() => setSelectedDay(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              Deadlines du{" "}
              {selectedDay && format(selectedDay.date, "d MMMM yyyy", { locale: fr })}
            </DialogTitle>
          </DialogHeader>
          <ScrollArea className="max-h-[60vh]">
            <div className="space-y-3">
              {selectedDay?.opportunities.map((opp) => (
                <Card key={opp.id}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <Link
                          href={`/leads/${opp.id}`}
                          className="font-medium hover:underline flex items-center gap-1"
                        >
                          {opp.title}
                          <ExternalLink className="h-3 w-3" />
                        </Link>
                        
                        {opp.organization_name && (
                          <div className="flex items-center gap-1 text-sm text-muted-foreground mt-1">
                            <Building2 className="h-4 w-4" />
                            {opp.organization_name}
                          </div>
                        )}
                        
                        {opp.budget_amount && (
                          <div className="flex items-center gap-1 text-sm mt-1">
                            <Euro className="h-4 w-4" />
                            {formatCurrency(opp.budget_amount)}
                          </div>
                        )}
                      </div>
                      
                      <Badge className={`${getScoreColor(opp.score)} text-white`}>
                        Score: {opp.score}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </>
  );
}
