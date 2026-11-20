"use client";

import { Suspense, useEffect, useState, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Landmark,
  RefreshCw,
  AlertTriangle,
  Settings2,
  Search,
  SlidersHorizontal,
  ArrowUpRight,
  ArrowDownLeft,
  Repeat,
  CreditCard,
  CheckCircle2,
  XCircle,
  ChevronDown,
  Calendar,
} from 'lucide-react';
import { RadarSpinner } from '@/components/ui/radar-loader';
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { AppLayout } from "@/components/layout/AppLayout";
import { useBankingStore } from "@/store/bankingStore";
import { useAuthStore } from "@/store/auth";
import type { RevolutTransaction } from "@/store/bankingStore";

// ============================================================================
// HELPERS
// ============================================================================

const MONTH_NAMES = [
  "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
];

const SHORT_MONTHS = [
  "janv.", "févr.", "mars", "avr.", "mai", "juin",
  "juil.", "août", "sept.", "oct.", "nov.", "déc.",
];

function getMonthKey(dateStr: string) {
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth()).padStart(2, "0")}`;
}

function getMonthLabel(dateStr: string) {
  const d = new Date(dateStr);
  return `${MONTH_NAMES[d.getMonth()]} ${d.getFullYear()}`;
}

function getDayInfo(dateStr: string) {
  const d = new Date(dateStr);
  return {
    day: String(d.getDate()).padStart(2, "0"),
    monthShort: SHORT_MONTHS[d.getMonth()],
  };
}

function classifyTransaction(tx: RevolutTransaction): { label: string; color: string } {
  const type = tx.type?.toLowerCase() || "";
  const mainLeg = tx.legs?.[0];
  const amount = mainLeg?.amount ?? 0;
  const desc = (mainLeg?.description || tx.reference || "").toLowerCase();

  if (type === "card_payment" || type === "atm") {
    return { label: "Carte bancaire", color: "text-blue-600 dark:text-blue-400" };
  }
  if (type === "transfer" && amount > 0) {
    if (desc.includes("pro") || desc.includes("business")) {
      return { label: "Apport personnel", color: "text-emerald-600 dark:text-emerald-400" };
    }
    return { label: "Recette", color: "text-emerald-600 dark:text-emerald-400" };
  }
  if (type === "transfer" && amount < 0) {
    if (desc.includes("personal") || desc.includes("perso")) {
      return { label: "Prélèvement personnel", color: "text-gray-700 dark:text-gray-300" };
    }
    return { label: "Virement sortant", color: "text-gray-700 dark:text-gray-300" };
  }
  if (type === "exchange") {
    return { label: "Change", color: "text-purple-600 dark:text-purple-400" };
  }
  if (type === "fee") {
    return { label: "Frais bancaires", color: "text-red-600 dark:text-red-400" };
  }
  if (type === "topup" || type === "top_up") {
    return { label: "Apport personnel", color: "text-emerald-600 dark:text-emerald-400" };
  }
  if (amount > 0) {
    return { label: "Recette", color: "text-emerald-600 dark:text-emerald-400" };
  }
  if (amount < 0) {
    return { label: "Prélèvement personnel", color: "text-gray-700 dark:text-gray-300" };
  }
  return { label: "Banque", color: "text-amber-600 dark:text-amber-400" };
}

function getTxIcon(tx: RevolutTransaction) {
  const amount = tx.legs?.[0]?.amount ?? 0;
  const type = tx.type?.toLowerCase() || "";
  if (type === "card_payment") return CreditCard;
  if (type === "exchange") return Repeat;
  if (amount > 0) return ArrowDownLeft;
  return ArrowUpRight;
}

function formatAmount(amount: number) {
  return new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

// ============================================================================
// MAIN PAGE CONTENT
// ============================================================================

function BankingPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuthStore();
  const {
    dashboard,
    connections,
    isLoading,
    error,
    fetchDashboard,
    revolutStatus,
    revolutTransactions,
    revolutTransactionsLoading,
    fetchRevolutStatus,
    syncRevolut,
    fetchRevolutTransactions,
  } = useBankingStore();

  const [searchQuery, setSearchQuery] = useState("");
  const [revolutSuccess, setRevolutSuccess] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [isSyncing, setIsSyncing] = useState(false);

  const isAdmin = user?.role === "admin" || user?.is_superuser === true;

  useEffect(() => {
    fetchDashboard();
    fetchRevolutStatus();
  }, [fetchDashboard, fetchRevolutStatus]);

  useEffect(() => {
    if (revolutStatus?.connected) {
      fetchRevolutTransactions({ count: 100 });
    }
  }, [revolutStatus?.connected, fetchRevolutTransactions]);

  useEffect(() => {
    const revolutConnected = searchParams.get("revolut_connected");
    const revolutError = searchParams.get("revolut_error");
    const accountsCount = searchParams.get("accounts");

    if (revolutConnected === "true") {
      setRevolutSuccess(`Revolut connecté ! ${accountsCount || 0} compte(s) synchronisé(s).`);
      fetchDashboard();
      fetchRevolutStatus();
      router.replace("/transactions");
    }
    if (revolutError) {
      useBankingStore.setState({
        error: `Erreur Revolut : ${decodeURIComponent(revolutError)}`,
      });
      router.replace("/transactions");
    }
  }, [searchParams, fetchDashboard, fetchRevolutStatus, router]);

  const totalBalance = useMemo(() => {
    if (dashboard?.total_balances?.["EUR"]) return dashboard.total_balances["EUR"];
    return 0;
  }, [dashboard]);

  const { groupedTransactions, filteredCount, allTypes } = useMemo(() => {
    let txs = [...revolutTransactions];
    const types = new Set<string>();
    txs.forEach((tx) => types.add(tx.type));

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      txs = txs.filter((tx) => {
        const desc = tx.legs?.[0]?.description || "";
        const ref = tx.reference || "";
        const merchant = tx.merchant?.name || "";
        return (
          desc.toLowerCase().includes(q) ||
          ref.toLowerCase().includes(q) ||
          merchant.toLowerCase().includes(q) ||
          tx.type.toLowerCase().includes(q)
        );
      });
    }

    if (typeFilter !== "all") {
      txs = txs.filter((tx) => tx.type === typeFilter);
    }

    txs.sort((a, b) => {
      const da = a.completed_at || a.created_at || "";
      const db = b.completed_at || b.created_at || "";
      return db.localeCompare(da);
    });

    const groups: Record<string, { label: string; date: string; transactions: RevolutTransaction[] }> = {};
    txs.forEach((tx) => {
      const dateStr = tx.completed_at || tx.created_at || "";
      if (!dateStr) return;
      const key = getMonthKey(dateStr);
      if (!groups[key]) {
        groups[key] = { label: getMonthLabel(dateStr), date: dateStr, transactions: [] };
      }
      groups[key].transactions.push(tx);
    });

    const sorted = Object.entries(groups)
      .sort(([a], [b]) => b.localeCompare(a))
      .map(([, v]) => v);

    return { groupedTransactions: sorted, filteredCount: txs.length, allTypes: Array.from(types) };
  }, [revolutTransactions, searchQuery, typeFilter]);

  const handleSync = async () => {
    setIsSyncing(true);
    await syncRevolut();
    await fetchRevolutTransactions({ count: 100 });
    setIsSyncing(false);
  };

  const formatCurrency = (val: number) =>
    new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(val);

  // ─── EMPTY / NOT CONNECTED ───────────────────────────────────────
  if (!isLoading && !revolutStatus?.connected && connections.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
        <div className="w-16 h-16 rounded-2xl bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center mb-6">
          <Landmark className="h-8 w-8 text-purple-600 dark:text-purple-400" />
        </div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
          Transactions
        </h2>
        <p className="text-gray-500 dark:text-gray-400 max-w-md mb-6">
          Connectez votre banque pour visualiser vos transactions en temps réel.
        </p>
        <Button onClick={() => router.push("/settings")} variant="outline" className="rounded-full px-5">
          <Settings2 className="h-4 w-4 mr-2" />
          Gérer dans les paramètres
        </Button>
      </div>
    );
  }

  // ─── MAIN VIEW ───────────────────────────────────────────────────
  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Transactions
        </h1>
      </div>

      {/* Error */}
      {error && (
        <div className="px-4 py-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-sm flex items-center gap-2 mb-6">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Success */}
      <AnimatePresence>
        {revolutSuccess && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="px-4 py-3 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800/50 text-emerald-700 dark:text-emerald-400 text-sm flex items-center gap-2 mb-6"
          >
            <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
            {revolutSuccess}
            <button onClick={() => setRevolutSuccess(null)} className="ml-auto text-emerald-500 hover:text-emerald-700">
              <XCircle className="h-4 w-4" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Summary + search/filter bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-end justify-between gap-4 mb-6">
        <div>
          <p className="text-xs text-gray-400 font-medium uppercase tracking-wider mb-0.5">
            Solde total
          </p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
            {formatCurrency(totalBalance)}
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Rechercher"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-2 text-sm rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-600/20 focus:border-purple-500 w-44 transition-all"
            />
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
            className={cn(
              "rounded-xl gap-1.5 h-[38px] px-3.5",
              showFilters && "border-purple-400 bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400",
            )}
          >
            <SlidersHorizontal className="h-4 w-4" />
            Filtrer
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="rounded-xl h-[38px] w-[38px]"
            onClick={handleSync}
            disabled={isSyncing}
          >
            <RefreshCw className={cn("h-4 w-4", isSyncing && "animate-spin")} />
          </Button>
        </div>
      </div>

      {/* Filters */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="flex flex-wrap items-center gap-2 pb-5">
              <button
                onClick={() => setTypeFilter("all")}
                className={cn(
                  "px-3 py-1.5 rounded-full text-xs font-medium border transition-all",
                  typeFilter === "all"
                    ? "bg-purple-600 text-white border-purple-600 shadow-sm shadow-purple-500/20"
                    : "bg-white dark:bg-slate-900 text-gray-500 border-gray-200 dark:border-slate-700 hover:border-purple-300 dark:hover:border-purple-700",
                )}
              >
                Tous
              </button>
              {allTypes.map((t) => (
                <button
                  key={t}
                  onClick={() => setTypeFilter(t)}
                  className={cn(
                    "px-3 py-1.5 rounded-full text-xs font-medium border transition-all capitalize",
                    typeFilter === t
                      ? "bg-purple-600 text-white border-purple-600 shadow-sm shadow-purple-500/20"
                      : "bg-white dark:bg-slate-900 text-gray-500 border-gray-200 dark:border-slate-700 hover:border-purple-300 dark:hover:border-purple-700",
                  )}
                >
                  {t.replace(/_/g, " ")}
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Transaction count */}
      <div className="flex items-center justify-end mb-5">
        <span className="text-sm text-gray-400 font-medium">
          {filteredCount} Transaction{filteredCount !== 1 ? "s" : ""}
        </span>
      </div>

      {/* ── TIMELINE ──────────────────────────────────────────────── */}
      {revolutTransactionsLoading && revolutTransactions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24">
          <RadarSpinner className="h-8 w-8 text-primary text-primary animate-spin mb-3" />
          <p className="text-sm text-gray-400">Chargement des transactions…</p>
        </div>
      ) : groupedTransactions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="w-14 h-14 rounded-2xl bg-gray-100 dark:bg-slate-800 flex items-center justify-center mb-4">
            <Calendar className="h-7 w-7 text-gray-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
            Aucune transaction
          </h3>
          <p className="text-sm text-gray-400 max-w-sm">
            {searchQuery ? "Aucun résultat pour cette recherche." : "Vos transactions apparaîtront ici après synchronisation."}
          </p>
        </div>
      ) : (
        <div className="space-y-10">
          {groupedTransactions.map((group, gi) => (
            <div key={gi}>
              {/* ── Month header ── */}
              <div className="flex items-center gap-2.5 mb-5">
                <div className="w-1.5 h-5 rounded-full bg-purple-600 dark:bg-purple-500" />
                <h2 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider">
                  {group.label}
                </h2>
              </div>

              {/* ── Transactions with timeline ── */}
              <div className="relative">
                {/* Vertical line */}
                <div className="absolute left-[28px] top-2 bottom-2 w-px bg-gray-200 dark:bg-slate-700/60" />

                <div className="space-y-1.5">
                  {group.transactions.map((tx, ti) => {
                    const dateStr = tx.completed_at || tx.created_at || "";
                    const { day, monthShort } = getDayInfo(dateStr);
                    const mainLeg = tx.legs?.[0];
                    const amount = mainLeg?.amount ?? 0;
                    const description = mainLeg?.description || tx.reference || tx.merchant?.name || tx.type;
                    const category = classifyTransaction(tx);
                    const TxIcon = getTxIcon(tx);
                    const isPositive = amount > 0;

                    const prevTx = ti > 0 ? group.transactions[ti - 1] : null;
                    const prevDate = prevTx ? getDayInfo(prevTx.completed_at || prevTx.created_at || "") : null;
                    const showDate = !prevDate || prevDate.day !== day;

                    return (
                      <div key={tx.id} className="flex items-start gap-0">
                        {/* Date column */}
                        <div className="w-[56px] flex-shrink-0 relative flex items-start justify-center pt-4">
                          {showDate && (
                            <>
                              <div className="absolute left-1/2 -translate-x-1/2 top-[22px] w-[7px] h-[7px] rounded-full bg-gray-300 dark:bg-slate-500 ring-[3px] ring-white dark:ring-slate-950 z-10" />
                              <div className="text-center">
                                <p className="text-[15px] font-bold text-gray-600 dark:text-gray-300 leading-none">
                                  {day}
                                </p>
                                <p className="text-[10px] text-gray-400 mt-0.5">
                                  {monthShort}
                                </p>
                              </div>
                            </>
                          )}
                        </div>

                        {/* Card */}
                        <div className="flex-1 min-w-0 ml-2">
                          <div className="group rounded-xl border border-gray-100 dark:border-slate-800/80 bg-white dark:bg-slate-900 px-4 py-3.5 flex items-center gap-3.5 hover:shadow-[0_1px_8px_rgba(0,0,0,0.04)] dark:hover:shadow-none hover:border-gray-200 dark:hover:border-slate-700 transition-all cursor-default">
                            {/* Icon */}
                            <div className="w-9 h-9 rounded-full bg-gray-50 dark:bg-slate-800 flex items-center justify-center flex-shrink-0 group-hover:bg-gray-100 dark:group-hover:bg-slate-700 transition-colors">
                              <TxIcon className="h-4 w-4 text-gray-400 dark:text-gray-500" />
                            </div>

                            {/* Description */}
                            <p className="flex-1 min-w-0 text-sm font-medium text-gray-800 dark:text-gray-200 truncate">
                              {description}
                            </p>

                            {/* Category */}
                            <span className={cn("text-xs font-bold whitespace-nowrap hidden sm:block", category.color)}>
                              {category.label}
                            </span>

                            {/* Amount */}
                            <p
                              className={cn(
                                "text-sm font-bold tabular-nums whitespace-nowrap min-w-[72px] text-right",
                                isPositive
                                  ? "text-emerald-600 dark:text-emerald-400"
                                  : "text-gray-900 dark:text-white",
                              )}
                            >
                              {isPositive ? "" : "-"}{formatAmount(Math.abs(amount))}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ))}

          {/* Load more */}
          {revolutTransactions.length >= 100 && (
            <div className="text-center pt-2 pb-8">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => fetchRevolutTransactions({ count: revolutTransactions.length + 100 })}
                disabled={revolutTransactionsLoading}
                className="text-gray-400 hover:text-gray-600"
              >
                {revolutTransactionsLoading ? (
                  <RadarSpinner className="h-4 w-4 mr-1.5 animate-spin" />
                ) : (
                  <ChevronDown className="h-4 w-4 mr-1.5" />
                )}
                Charger plus de transactions
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// PAGE EXPORT
// ============================================================================

export default function BankingPage() {
  return (
    <AppLayout>
      <Suspense
        fallback={
          <div className="flex items-center justify-center min-h-[60vh]">
            <RadarSpinner className="h-8 w-8 animate-spin text-primary" />
          </div>
        }
      >
        <BankingPageContent />
      </Suspense>
    </AppLayout>
  );
}
