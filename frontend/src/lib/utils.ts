import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(amount: number | null | undefined, currency = "EUR"): string {
  if (amount == null) return "-";
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return "-";
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(date));
}

export function formatDateTime(date: string | Date | null | undefined): string {
  if (!date) return "-";
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(date));
}

export function formatRelativeDate(date: string | Date | null | undefined): string {
  if (!date) return "-";
  const now = new Date();
  const target = new Date(date);
  const diffMs = target.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return `Il y a ${Math.abs(diffDays)} j`;
  if (diffDays === 0) return "Aujourd'hui";
  if (diffDays === 1) return "Demain";
  if (diffDays < 7) return `Dans ${diffDays} j`;
  if (diffDays < 30) return `Dans ${Math.floor(diffDays / 7)} sem`;
  return formatDate(date);
}

export function getScoreColor(score: number | null | undefined): string {
  if (score == null) return "text-gray-400";
  if (score >= 10) return "text-green-600";
  if (score >= 5) return "text-yellow-600";
  return "text-red-600";
}

export function getScoreBgColor(score: number | null | undefined): string {
  if (score == null) return "bg-gray-100";
  if (score >= 10) return "bg-green-100";
  if (score >= 5) return "bg-yellow-100";
  return "bg-red-100";
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    new: "bg-blue-100 text-blue-800",
    to_qualify: "bg-yellow-100 text-yellow-800",
    qualified: "bg-purple-100 text-purple-800",
    in_progress: "bg-orange-100 text-orange-800",
    submitted: "bg-indigo-100 text-indigo-800",
    won: "bg-green-100 text-green-800",
    lost: "bg-red-100 text-red-800",
    archived: "bg-gray-100 text-gray-800",
  };
  return colors[status] || "bg-gray-100 text-gray-800";
}

export function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    new: "Nouveau",
    to_qualify: "À qualifier",
    qualified: "Qualifié",
    in_progress: "En cours",
    submitted: "Soumis",
    won: "Gagné",
    lost: "Perdu",
    archived: "Archivé",
  };
  return labels[status] || status;
}

export function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    appel_offres: "Appel d'offres",
    partenariat: "Partenariat",
    sponsoring: "Sponsoring",
    privatisation: "Privatisation",
    production: "Production",
    prestation: "Prestation",
    autre: "Autre",
  };
  return labels[category] || category;
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + "...";
}
