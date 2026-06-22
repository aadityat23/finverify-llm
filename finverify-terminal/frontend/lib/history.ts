/**
 * Query History — Shared helpers (Session 12A)
 * ==============================================
 * Shared between the terminal (page.tsx) and dashboard (dashboard/page.tsx).
 * Uses localStorage for anonymous users; Supabase syncs when authenticated.
 */

import type { QueryResponse, CorrectionEntry } from "@/lib/api";

export interface HistoryEntry {
  id: string;
  question: string;
  raw_number: number | null;
  verified_number: number | null;
  trust_score: string;
  trust_color: string;
  correction_log: CorrectionEntry[];
  display_value: string;
  timestamp: string;
}

export type TrustFilter = "ALL" | "HIGH" | "MEDIUM" | "LOW";

const STORAGE_KEY = "finverify_query_history";

export function loadHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveHistoryLocal(entries: HistoryEntry[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries.slice(0, 100)));
}

export function addToHistory(result: QueryResponse) {
  const entry: HistoryEntry = {
    id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
    question: result.question,
    raw_number: result.raw_number,
    verified_number: result.verified_number,
    trust_score: result.trust_score,
    trust_color: result.trust_color,
    correction_log: result.correction_log,
    display_value: result.display_value,
    timestamp: new Date().toISOString(),
  };
  const existing = loadHistory();
  saveHistoryLocal([entry, ...existing]);
}
