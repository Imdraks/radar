'use client';
import { workspaceFetch } from "@/lib/workspace-fetch";

import { useState, useEffect, useMemo } from 'react';
import {
  Calendar as CalendarIcon,
  Plus,
  ChevronLeft,
  ChevronRight,
  Loader2,
  X,
  MapPin,
  Clock,
} from 'lucide-react';
import { AppLayoutWithOnboarding, ProtectedRoute } from "@/components/layout";

interface CalendarEvent {
  id: number;
  project_id?: number;
  title: string;
  type: string;
  start: string;
  end?: string;
  all_day: boolean;
  location?: string;
  notes?: string;
  project_name?: string;
  client_name?: string;
}

interface Project {
  id: number;
  name: string;
  client_name?: string;
}

const EVENT_COLORS: Record<string, string> = {
  shoot: 'bg-red-500',
  delivery: 'bg-green-500',
  meeting: 'bg-blue-500',
  deadline: 'bg-amber-500',
  other: 'bg-purple-500',
};

const EVENT_LABELS: Record<string, string> = {
  shoot: 'Tournage',
  delivery: 'Livraison',
  meeting: 'Réunion',
  deadline: 'Deadline',
  other: 'Autre',
};

export default function CalendarPage() {
  return (
    <ProtectedRoute>
      <AppLayoutWithOnboarding>
        <CalendarContent />
      </AppLayoutWithOnboarding>
    </ProtectedRoute>
  );
}

function CalendarContent() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [currentMonth, setCurrentMonth] = useState(new Date());

  // Form state
  const [newEvent, setNewEvent] = useState({
    title: '',
    project_id: '',
    type: 'other',
    start: '',
    end: '',
    all_day: false,
    location: '',
    notes: '',
  });

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      
      // Get events for current month ± 1 month
      const startDate = new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1);
      const endDate = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 2, 0);
      
      const params = new URLSearchParams({
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString(),
      });
      
      const [eventsRes, projectsRes] = await Promise.all([
        workspaceFetch(`/api/v1/agency/calendar?${params}`, {
          headers: { 'Authorization': `Bearer ${token}` },
        }),
        workspaceFetch('/api/v1/agency/projects', {
          headers: { 'Authorization': `Bearer ${token}` },
        }),
      ]);
      
      if (eventsRes.ok) {
        setEvents(await eventsRes.json());
      }
      if (projectsRes.ok) {
        setProjects(await projectsRes.json());
      }
    } catch (err) {
      console.error('Failed to fetch calendar:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [currentMonth]);

  const handleCreateEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const token = localStorage.getItem('access_token');
      const response = await workspaceFetch('/api/v1/agency/calendar', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...newEvent,
          project_id: newEvent.project_id ? parseInt(newEvent.project_id) : null,
          start: newEvent.start || selectedDate.toISOString(),
          end: newEvent.end || null,
        }),
      });
      
      if (response.ok) {
        setShowAddModal(false);
        setNewEvent({ title: '', project_id: '', type: 'other', start: '', end: '', all_day: false, location: '', notes: '' });
        await fetchData();
      }
    } catch (err) {
      console.error('Failed to create event:', err);
    }
  };

  const handleDeleteEvent = async (eventId: number) => {
    if (!confirm('Supprimer cet événement ?')) return;
    
    try {
      const token = localStorage.getItem('access_token');
      await workspaceFetch(`/api/v1/agency/calendar/${eventId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      await fetchData();
    } catch (err) {
      console.error('Failed to delete event:', err);
    }
  };

  // Calendar helpers
  const getDaysInMonth = (date: Date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const days: Date[] = [];
    
    // Add padding days from previous month
    const startPadding = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1;
    for (let i = startPadding - 1; i >= 0; i--) {
      days.push(new Date(year, month, -i));
    }
    
    // Add days of current month
    for (let i = 1; i <= lastDay.getDate(); i++) {
      days.push(new Date(year, month, i));
    }
    
    // Add padding days from next month
    const endPadding = 42 - days.length;
    for (let i = 1; i <= endPadding; i++) {
      days.push(new Date(year, month + 1, i));
    }
    
    return days;
  };

  const getEventsForDate = (date: Date) => {
    return events.filter((event) => {
      const eventDate = new Date(event.start);
      return (
        eventDate.getFullYear() === date.getFullYear() &&
        eventDate.getMonth() === date.getMonth() &&
        eventDate.getDate() === date.getDate()
      );
    });
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('fr-FR', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  };

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const days = getDaysInMonth(currentMonth);
  const selectedDateEvents = getEventsForDate(selectedDate);

  const prevMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1));
  };

  const nextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1));
  };

  const isToday = (date: Date) => {
    const today = new Date();
    return (
      date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear()
    );
  };

  const isSelected = (date: Date) => {
    return (
      date.getDate() === selectedDate.getDate() &&
      date.getMonth() === selectedDate.getMonth() &&
      date.getFullYear() === selectedDate.getFullYear()
    );
  };

  const isCurrentMonth = (date: Date) => {
    return date.getMonth() === currentMonth.getMonth();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
      </div>
    );
  }

  return (
    <div className="p-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Calendrier</h1>
          <p className="text-gray-600">{events.length} événements ce mois</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
        >
          <Plus className="h-4 w-4" />
          Nouvel événement
        </button>
      </div>

      <div className="flex-1 flex gap-6 overflow-hidden">
        {/* Calendar Grid */}
        <div className="flex-1 bg-white rounded-xl border border-gray-100 p-4">
          {/* Month Navigation */}
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">
              {currentMonth.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })}
            </h2>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentMonth(new Date())}
                className="px-3 py-1 text-sm text-purple-600 hover:bg-purple-50 rounded"
              >
                Aujourd'hui
              </button>
              <button
                onClick={prevMonth}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <button
                onClick={nextMonth}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Days Header */}
          <div className="grid grid-cols-7 mb-2">
            {['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'].map((day) => (
              <div key={day} className="text-center text-sm font-medium text-gray-500 py-2">
                {day}
              </div>
            ))}
          </div>

          {/* Days Grid */}
          <div className="grid grid-cols-7 gap-1">
            {days.map((date, i) => {
              const dayEvents = getEventsForDate(date);
              const hasEvents = dayEvents.length > 0;
              
              return (
                <button
                  key={i}
                  onClick={() => setSelectedDate(date)}
                  className={`
                    aspect-square p-1 rounded-lg text-sm transition-colors relative
                    ${isCurrentMonth(date) ? 'text-gray-900' : 'text-gray-400'}
                    ${isSelected(date) ? 'bg-purple-100 text-purple-700' : 'hover:bg-gray-50'}
                    ${isToday(date) ? 'font-bold ring-2 ring-purple-500' : ''}
                  `}
                >
                  <span>{date.getDate()}</span>
                  {hasEvents && (
                    <div className="absolute bottom-1 left-1/2 -translate-x-1/2 flex gap-0.5">
                      {dayEvents.slice(0, 3).map((event, j) => (
                        <div
                          key={j}
                          className={`w-1.5 h-1.5 rounded-full ${EVENT_COLORS[event.type]}`}
                        />
                      ))}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Selected Day Events */}
        <div className="w-80 bg-white rounded-xl border border-gray-100 p-4 overflow-hidden flex flex-col">
          <h3 className="font-semibold text-gray-900 mb-4">
            {formatDate(selectedDate)}
          </h3>
          
          <div className="flex-1 overflow-y-auto space-y-3">
            {selectedDateEvents.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <CalendarIcon className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                <p className="text-sm">Aucun événement</p>
              </div>
            ) : (
              selectedDateEvents.map((event) => (
                <div
                  key={event.id}
                  className="bg-gray-50 rounded-lg p-3 group"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${EVENT_COLORS[event.type]}`} />
                      <span className="text-xs text-gray-500">{EVENT_LABELS[event.type]}</span>
                    </div>
                    <button
                      onClick={() => handleDeleteEvent(event.id)}
                      className="p-1 hover:bg-gray-200 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X className="h-3 w-3 text-gray-400" />
                    </button>
                  </div>
                  
                  <h4 className="font-medium text-gray-900 mt-1">{event.title}</h4>
                  
                  {event.project_name && (
                    <p className="text-sm text-gray-600 mt-1">{event.project_name}</p>
                  )}
                  
                  <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                    {!event.all_day && (
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatTime(event.start)}
                      </span>
                    )}
                    {event.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        {event.location}
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
          
          <button
            onClick={() => {
              setNewEvent({
                ...newEvent,
                start: selectedDate.toISOString().split('T')[0] + 'T09:00',
              });
              setShowAddModal(true);
            }}
            className="mt-4 w-full py-2 text-sm text-purple-600 bg-purple-50 rounded-lg hover:bg-purple-100 transition-colors flex items-center justify-center gap-1"
          >
            <Plus className="h-4 w-4" />
            Ajouter un événement
          </button>
        </div>
      </div>

      {/* Add Event Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold">Nouvel événement</h2>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <form onSubmit={handleCreateEvent} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Titre *
                </label>
                <input
                  type="text"
                  required
                  value={newEvent.title}
                  onChange={(e) => setNewEvent({ ...newEvent, title: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  placeholder="Ex: Tournage clip"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Type
                  </label>
                  <select
                    value={newEvent.type}
                    onChange={(e) => setNewEvent({ ...newEvent, type: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  >
                    <option value="shoot">Tournage</option>
                    <option value="delivery">Livraison</option>
                    <option value="meeting">Réunion</option>
                    <option value="deadline">Deadline</option>
                    <option value="other">Autre</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Projet
                  </label>
                  <select
                    value={newEvent.project_id}
                    onChange={(e) => setNewEvent({ ...newEvent, project_id: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  >
                    <option value="">Aucun projet</option>
                    {projects.map((project) => (
                      <option key={project.id} value={project.id}>
                        {project.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Date/heure début *
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={newEvent.start}
                    onChange={(e) => setNewEvent({ ...newEvent, start: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Date/heure fin
                  </label>
                  <input
                    type="datetime-local"
                    value={newEvent.end}
                    onChange={(e) => setNewEvent({ ...newEvent, end: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  />
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="all_day"
                  checked={newEvent.all_day}
                  onChange={(e) => setNewEvent({ ...newEvent, all_day: e.target.checked })}
                  className="rounded text-purple-600 focus:ring-purple-500"
                />
                <label htmlFor="all_day" className="text-sm text-gray-700">
                  Journée entière
                </label>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Lieu
                </label>
                <input
                  type="text"
                  value={newEvent.location}
                  onChange={(e) => setNewEvent({ ...newEvent, location: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  placeholder="Ex: Studio Paris"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Notes
                </label>
                <textarea
                  value={newEvent.notes}
                  onChange={(e) => setNewEvent({ ...newEvent, notes: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  rows={2}
                  placeholder="Notes additionnelles..."
                />
              </div>
              
              <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                >
                  Créer l'événement
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
