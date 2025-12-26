"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Bell, X, Check, AlertTriangle, Info, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAuthStore } from "@/store/auth";
import { formatDistanceToNow } from "date-fns";
import { fr } from "date-fns/locale";

interface Notification {
  id: string;
  type: "new_opportunity" | "deadline" | "high_score" | "update" | "alert";
  title: string;
  message: string;
  opportunityId?: string;
  read: boolean;
  createdAt: string;
  priority: "low" | "medium" | "high";
}

const STORAGE_KEY = "notifications_cache";

// Build WebSocket URL dynamically based on API URL
const getWsUrl = () => {
  if (typeof window === 'undefined') return '';
  
  // Use the API URL from environment or fallback to backend port
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  
  // Convert http(s) to ws(s)
  const wsUrl = apiUrl.replace(/^http/, 'ws');
  
  return `${wsUrl}/ws`;
};

export function NotificationCenter() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 3; // Limit reconnection attempts
  
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  
  // Get token from localStorage
  const getToken = () => typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;

  // Load cached notifications
  useEffect(() => {
    const cached = localStorage.getItem(STORAGE_KEY);
    if (cached) {
      try {
        setNotifications(JSON.parse(cached));
      } catch (e) {
        console.error("Failed to parse cached notifications:", e);
      }
    }
  }, []);

  // Save notifications to cache
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(notifications.slice(0, 50)));
  }, [notifications]);

  // WebSocket connection
  const connectWebSocket = useCallback(() => {
    const token = getToken();
    if (!token || !user) return;

    // Avoid creating multiple connections (React StrictMode double-mount)
    if (wsRef.current && wsRef.current.readyState === WebSocket.CONNECTING) {
      return;
    }

    try {
      const wsUrl = getWsUrl();
      if (!wsUrl) return;
      
      const ws = new WebSocket(`${wsUrl}/notifications?token=${token}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttempts.current = 0; // Reset on successful connection
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === "notification") {
            const notification: Notification = {
              id: crypto.randomUUID(),
              type: data.notification_type || "update",
              title: data.title,
              message: data.message,
              opportunityId: data.opportunity_id,
              read: false,
              createdAt: new Date().toISOString(),
              priority: data.priority || "medium",
            };

            setNotifications((prev) => [notification, ...prev]);

            // Show browser notification if permitted
            if (Notification.permission === "granted") {
              new Notification(notification.title, {
                body: notification.message,
                icon: "/icon.png",
              });
            }

            // Refresh opportunities list
            if (data.notification_type === "new_opportunity") {
              queryClient.invalidateQueries({ queryKey: ["opportunities"] });
            }
          }
        } catch {
          // Silently ignore parse errors
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        
        // Only reconnect if we haven't exceeded max attempts
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket();
          }, 5000 * reconnectAttempts.current); // Exponential backoff
        }
        // After max attempts, stop trying (WebSocket not available on server)
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // Silently ignore WebSocket creation errors
    }
  }, [user, queryClient]);

  // Connect on mount
  useEffect(() => {
    connectWebSocket();

    // Request browser notification permission
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }

    return () => {
      wsRef.current?.close();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connectWebSocket]);

  const handleMarkAsRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  };

  const handleMarkAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const handleDismiss = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  const handleClearAll = () => {
    setNotifications([]);
  };

  const unreadCount = notifications.filter((n) => !n.read).length;

  const getNotificationIcon = (type: Notification["type"]) => {
    switch (type) {
      case "new_opportunity":
        return <Star className="h-4 w-4 text-blue-500" />;
      case "deadline":
        return <AlertTriangle className="h-4 w-4 text-orange-500" />;
      case "high_score":
        return <Star className="h-4 w-4 text-green-500" />;
      case "alert":
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      default:
        return <Info className="h-4 w-4 text-gray-500" />;
    }
  };

  const getPriorityColor = (priority: Notification["priority"]) => {
    switch (priority) {
      case "high":
        return "border-l-red-500";
      case "medium":
        return "border-l-orange-500";
      default:
        return "border-l-gray-300";
    }
  };

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center text-xs"
            >
              {unreadCount > 9 ? "9+" : unreadCount}
            </Badge>
          )}
          {/* Connection indicator */}
          <span
            className={`absolute bottom-0 right-0 h-2 w-2 rounded-full ${
              isConnected ? "bg-green-500" : "bg-red-500"
            }`}
          />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-96 p-0" align="end">
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold">Notifications</h3>
            {unreadCount > 0 && (
              <Badge variant="secondary">{unreadCount} non lues</Badge>
            )}
          </div>
          <div className="flex gap-1">
            {unreadCount > 0 && (
              <Button size="sm" variant="ghost" onClick={handleMarkAllAsRead}>
                <Check className="h-4 w-4" />
              </Button>
            )}
            {notifications.length > 0 && (
              <Button size="sm" variant="ghost" onClick={handleClearAll}>
                Effacer
              </Button>
            )}
          </div>
        </div>

        <ScrollArea className="h-96">
          {notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
              <Bell className="h-12 w-12 mb-4 opacity-20" />
              <p>Aucune notification</p>
            </div>
          ) : (
            <div className="divide-y">
              {notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`p-4 hover:bg-muted/50 transition-colors border-l-4 ${
                    getPriorityColor(notification.priority)
                  } ${notification.read ? "opacity-60" : ""}`}
                >
                  <div className="flex gap-3">
                    <div className="shrink-0 mt-1">
                      {getNotificationIcon(notification.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <p className="font-medium text-sm truncate">
                          {notification.title}
                        </p>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="shrink-0 h-6 w-6"
                          onClick={() => handleDismiss(notification.id)}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        {notification.message}
                      </p>
                      <div className="flex items-center justify-between mt-2">
                        <span className="text-xs text-muted-foreground">
                          {formatDistanceToNow(new Date(notification.createdAt), {
                            addSuffix: true,
                            locale: fr,
                          })}
                        </span>
                        {!notification.read && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 text-xs"
                            onClick={() => handleMarkAsRead(notification.id)}
                          >
                            Marquer comme lu
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>

        <div className="p-2 border-t text-center">
          <span
            className={`text-xs ${isConnected ? "text-green-600" : "text-red-600"}`}
          >
            {isConnected ? "● Connecté en temps réel" : "○ Déconnecté"}
          </span>
        </div>
      </PopoverContent>
    </Popover>
  );
}

// Hook for triggering notifications from other components
export function useNotifications() {
  const addNotification = useCallback((notification: Omit<Notification, "id" | "createdAt" | "read">) => {
    const event = new CustomEvent("add-notification", {
      detail: {
        ...notification,
        id: crypto.randomUUID(),
        createdAt: new Date().toISOString(),
        read: false,
      },
    });
    window.dispatchEvent(event);
  }, []);

  return { addNotification };
}
