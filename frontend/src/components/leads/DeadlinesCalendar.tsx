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
import { opportunitiesApi, googleCalendarApi, GoogleCalendarEvent } from "@/lib/api";
import { Opportunity } from "@/lib/types";
import { formatCurrency, getScoreColor } from "@/lib/utils";
import {
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
  Euro,
  Building2,
  ExternalLink,
} from 'lucide-react';
import { RadarSpinner } from '@/components/ui/radar-loader';
import Link from "next/link";

// Type pour les items du calendrier (deadline ou événement Google)
interface CalendarItem {
  id: string;
  title: string;
  type: "deadline" | "google";
  opportunity?: Opportunity;
  googleEvent?: GoogleCalendarEvent;
  score?: number;
}

interface CalendarDayProps {
  date: Date;
  items: CalendarItem[];
  isCurrentMonth: boolean;
  onDayClick: (date: Date, items: CalendarItem[]) => void;
}

function getItemColor(item: CalendarItem): string {
  if (item.type === "google") {
    return "bg-blue-500";
  }
  return getScoreColor(item.score);
}

function CalendarDay({
  date,
  items,
  isCurrentMonth,
  onDayClick,
}: CalendarDayProps) {
  const hasItems = items.length > 0;
  const isCurrentDay = isToday(date);
  const urgentCount = items.filter((i) => i.type === "deadline" && (i.score ?? 0) >= 10).length;
  const googleCount = items.filter((i) => i.type === "google").length;

  return (
    <button
      onClick={() => hasItems && onDayClick(date, items)}
      disabled={!hasItems}
      className={`
        min-h-[100px] p-2 border border-border rounded-lg text-left transition-colors
        ${!isCurrentMonth ? "bg-muted/30 text-muted-foreground" : "bg-card hover:bg-accent"}
        ${isCurrentDay ? "ring-2 ring-primary" : ""}
        ${hasItems ? "cursor-pointer" : "cursor-default"}
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
        {hasItems && (
          <div className="flex gap-1">
            {googleCount > 0 && (
              <Badge variant="outline" className="text-xs bg-blue-100 text-blue-700 border-blue-300">
                {googleCount}
              </Badge>
            )}
            {urgentCount > 0 && (
              <Badge variant="destructive" className="text-xs">
                {urgentCount}
              </Badge>
            )}
            {items.length - googleCount - urgentCount > 0 && (
              <Badge variant="secondary" className="text-xs">
                {items.length - googleCount - urgentCount}
              </Badge>
            )}
          </div>
        )}
      </div>
      
      {hasItems && (
        <div className="space-y-1">
          {items.slice(0, 3).map((item) => (
            <div
              key={item.id}
              className={`text-xs p-1 rounded truncate ${getItemColor(item)} text-white`}
            >
              {item.title}
            </div>
          ))}
          {items.length > 3 && (
            <div className="text-xs text-muted-foreground">
              +{items.length - 3} autres
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
    items: CalendarItem[];
  } | null>(null);

  // Fetch opportunities
  const { data: oppData, isLoading: isLoadingOpps } = useQuery({
    queryKey: ["opportunities", "calendar"],
    queryFn: () => opportunitiesApi.getAll({ limit: 500 }),
  });

  // Check Google Calendar connection status
  const { data: calendarStatus, isLoading: isLoadingStatus } = useQuery({
    queryKey: ["google-calendar-status"],
    queryFn: () => googleCalendarApi.getStatus(),
    retry: false,
  });

  // Calculate date range for fetching events
  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(currentDate);

  // Fetch Google Calendar events if connected
  const { data: googleEvents, isLoading: isLoadingEvents } = useQuery({
    queryKey: ["google-calendar-events", format(monthStart, "yyyy-MM-dd"), format(monthEnd, "yyyy-MM-dd")],
    queryFn: () => googleCalendarApi.listEvents(
      format(monthStart, "yyyy-MM-dd"),
      format(monthEnd, "yyyy-MM-dd")
    ),
    enabled: calendarStatus?.connected === true,
    retry: false,
  });

  // Extract items from paginated response
  const opportunities = oppData?.items || [];

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

  // Combine opportunities and Google events by date
  const itemsByDate = useMemo(() => {
    const map = new Map<string, CalendarItem[]>();
    
    // Add opportunities (deadlines)
    opportunities.forEach((opp: Opportunity) => {
      if (opp.deadline_at) {
        const dateKey = format(parseISO(opp.deadline_at), "yyyy-MM-dd");
        const existing = map.get(dateKey) || [];
        map.set(dateKey, [...existing, {
          id: `opp-${opp.id}`,
          title: opp.title,
          type: "deadline" as const,
          opportunity: opp,
          score: opp.score,
        }]);
      }
    });

    // Add Google Calendar events
    if (googleEvents && Array.isArray(googleEvents)) {
      googleEvents.forEach((event: GoogleCalendarEvent) => {
        if (event.start) {
          // Parse the start date (can be date or datetime)
          const startDate = event.start.includes("T") 
            ? parseISO(event.start) 
            : parseISO(event.start + "T00:00:00");
          const dateKey = format(startDate, "yyyy-MM-dd");
          const existing = map.get(dateKey) || [];
          map.set(dateKey, [...existing, {
            id: `google-${event.id}`,
            title: event.summary || "Sans titre",
            type: "google" as const,
            googleEvent: event,
          }]);
        }
      });
    }
    
    return map;
  }, [opportunities, googleEvents]);

  const getItemsForDate = (date: Date) => {
    const dateKey = format(date, "yyyy-MM-dd");
    return itemsByDate.get(dateKey) || [];
  };

  const handleDayClick = (date: Date, items: CalendarItem[]) => {
    setSelectedDay({ date, items });
  };

  const goToPreviousMonth = () => setCurrentDate(subMonths(currentDate, 1));
  const goToNextMonth = () => setCurrentDate(addMonths(currentDate, 1));
  const goToToday = () => setCurrentDate(new Date());

  const isLoading = isLoadingOpps || isLoadingStatus;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RadarSpinner className="h-8 w-8 text-primary" />
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
          {/* Google Calendar loading indicator */}
          {isLoadingEvents && calendarStatus?.connected && (
            <div className="flex items-center gap-2 mb-4 text-sm text-muted-foreground">
              <RadarSpinner className="h-4 w-4 animate-spin" />
              Chargement des événements Google Calendar...
            </div>
          )}

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
                items={getItemsForDate(date)}
                isCurrentMonth={isSameMonth(date, currentDate)}
                onDayClick={handleDayClick}
              />
            ))}
          </div>

          {/* Legend */}
          <div className="flex flex-wrap items-center gap-4 mt-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-blue-500"></div>
              <span>Google Calendar</span>
            </div>
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
              Événements du{" "}
              {selectedDay && format(selectedDay.date, "d MMMM yyyy", { locale: fr })}
            </DialogTitle>
          </DialogHeader>
          <ScrollArea className="max-h-[60vh]">
            <div className="space-y-3">
              {/* Google Calendar Events */}
              {selectedDay?.items.filter(i => i.type === "google").map((item) => (
                <Card key={item.id} className="border-blue-200 bg-blue-50/50">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        {item.googleEvent?.html_link ? (
                          <a
                            href={item.googleEvent.html_link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-medium hover:underline flex items-center gap-1 text-blue-700"
                          >
                            {item.title}
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        ) : (
                          <span className="font-medium text-blue-700">{item.title}</span>
                        )}
                        
                        {item.googleEvent?.location && (
                          <div className="text-sm text-muted-foreground mt-1">
                            {item.googleEvent.location}
                          </div>
                        )}
                        
                        {item.googleEvent?.description && (
                          <div className="text-sm text-muted-foreground mt-1 line-clamp-2">
                            {item.googleEvent.description}
                          </div>
                        )}
                        
                        {item.googleEvent?.start && !item.googleEvent.all_day && (
                          <div className="text-sm text-muted-foreground mt-1">
                            🕐 {item.googleEvent.start.includes("T") 
                              ? format(parseISO(item.googleEvent.start), "HH:mm", { locale: fr })
                              : "Journée entière"
                            }
                            {item.googleEvent?.end && item.googleEvent.end.includes("T") && (
                              <> - {format(parseISO(item.googleEvent.end), "HH:mm", { locale: fr })}</>
                            )}
                          </div>
                        )}
                      </div>
                      
                      <Badge variant="outline" className="bg-blue-100 text-blue-700 border-blue-300">
                        Google
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}

              {/* Opportunity Deadlines */}
              {selectedDay?.items.filter(i => i.type === "deadline").map((item) => (
                <Card key={item.id}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <Link
                          href={`/leads/${item.opportunity?.id}`}
                          className="font-medium hover:underline flex items-center gap-1"
                        >
                          {item.title}
                          <ExternalLink className="h-3 w-3" />
                        </Link>
                        
                        {item.opportunity?.organization_name && (
                          <div className="flex items-center gap-1 text-sm text-muted-foreground mt-1">
                            <Building2 className="h-4 w-4" />
                            {item.opportunity.organization_name}
                          </div>
                        )}
                        
                        {item.opportunity?.budget_amount && (
                          <div className="flex items-center gap-1 text-sm mt-1">
                            <Euro className="h-4 w-4" />
                            {formatCurrency(item.opportunity.budget_amount)}
                          </div>
                        )}
                      </div>
                      
                      <Badge className={`${getScoreColor(item.score)} text-white`}>
                        Score: {item.score}
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
