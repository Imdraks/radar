"use client";

import { useEffect, useState, createContext, useContext, ReactNode } from "react";
import { X, CheckCircle, AlertCircle, Info, Bell } from "lucide-react";
import { Toaster as SonnerToaster } from "sonner";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";

interface Toast {
  id: string;
  title: string;
  description?: string;
  type: "success" | "error" | "info" | "warning";
  duration?: number;
}

interface ToastContextType {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id">) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = (toast: Omit<Toast, "id">) => {
    const id = Math.random().toString(36).substring(2, 9);
    const newToast = { ...toast, id };
    setToasts((prev) => [...prev, newToast]);

    // Auto-remove after duration
    const duration = toast.duration || 5000;
    setTimeout(() => {
      removeToast(id);
    }, duration);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
      <ExistingSonnerNotifications />
    </ToastContext.Provider>
  );
}

function ToastContainer({ toasts, removeToast }: { toasts: Toast[]; removeToast: (id: string) => void }) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-md">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  const icons = {
    success: CheckCircle,
    error: AlertCircle,
    info: Info,
    warning: Bell,
  };
  const Icon = icons[toast.type];

  const colors = {
    success: "border-l-green-500",
    error: "border-l-red-500",
    info: "border-l-blue-500",
    warning: "border-l-amber-500",
  };

  return (
    <div
      className={cn(
        "flex items-start gap-3 border border-border border-l-4 bg-popover text-popover-foreground p-4 rounded-lg shadow-lg animate-in slide-in-from-right-full duration-200",
        colors[toast.type]
      )}
    >
      <Icon className="h-5 w-5 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="font-medium">{toast.title}</p>
        {toast.description && (
          <p className="text-sm opacity-90 mt-1">{toast.description}</p>
        )}
      </div>
      <button
        type="button"
        aria-label="Fermer la notification"
        onClick={onClose}
        className="flex-shrink-0 p-1 rounded hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-colors"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

// Several existing business pages already emit Sonner toasts; render them once.
function ExistingSonnerNotifications() {
  const { resolvedTheme } = useTheme();
  return <SonnerToaster theme={resolvedTheme === 'dark' ? 'dark' : 'light'} position="bottom-right" richColors closeButton containerAriaLabel="Notifications Radar" />;
}
