"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  verifyNumber,
} from "@/lib/api";
import {
  type HistoryEntry,
  type TrustFilter,
  loadHistory,
  saveHistoryLocal,
} from "@/lib/history";

/**
 * Dashboard
 * Shows query history with DVL outcomes.
 * Filter by trust level, re-run past queries.
 * Uses localStorage for persistence (Clerk auth stripped, Session 2.3).
 */



/* ── Trust badge ── */
function TrustBadge({ trust }: { trust: string }) {
  const cls =
    trust === "HIGH"
      ? "bg-t-green/10 text-t-green border-t-green/20"
      : trust === "MEDIUM"
      ? "bg-t-amber/10 text-t-amber border-t-amber/20"
      : trust === "LOW"
      ? "bg-t-red/10 text-t-red border-t-red/20"
      : "bg-white/5 text-t-muted border-t-border/30";
  return (
    <span className={`text-[8px] font-mono font-bold px-1.5 py-0.5 rounded border ${cls}`}>
      {trust}
    </span>
  );
}

/* ── History row ── */
function HistoryRow({
  entry,
  onRerun,
  rerunning,
}: {
  entry: HistoryEntry;
  onRerun: (e: HistoryEntry) => void;
  rerunning: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const time = new Date(entry.timestamp).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

  return (
    <div className="border-b border-t-border/30 last:border-b-0">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-4 py-2.5 hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-3">
          <span
            className={`w-[6px] h-[6px] rounded-full shrink-0 ${
              entry.trust_score === "HIGH"
                ? "bg-t-green"
                : entry.trust_score === "MEDIUM"
                ? "bg-t-amber"
                : "bg-t-red"
            }`}
          />
          <div className="flex-1 min-w-0">
            <div className="text-[11px] font-mono text-t-secondary truncate">
              {entry.question}
            </div>
            <div className="flex items-center gap-3 mt-0.5">
              <span className="text-[9px] font-mono text-t-muted">{time}</span>
              {entry.correction_log.length > 0 && (
                <span className="text-[8px] font-mono text-t-amber">
                  {entry.correction_log.length} correction{entry.correction_log.length > 1 ? "s" : ""}
                </span>
              )}
            </div>
          </div>
          <span className="text-[12px] font-mono font-bold text-t-primary tabular-nums shrink-0">
            {entry.display_value}
          </span>
          <TrustBadge trust={entry.trust_score} />
          <span className="text-[9px] text-t-muted">{expanded ? "▼" : "▶"}</span>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-3 ml-[18px]">
          <div className="panel p-3 bg-[#0d0d0d] space-y-2">
            <div className="flex gap-6 text-[10px] font-mono">
              <div>
                <span className="text-t-muted">RAW: </span>
                <span className="text-t-secondary tabular-nums">
                  {entry.raw_number?.toFixed(4) ?? "N/A"}
                </span>
              </div>
              <div>
                <span className="text-t-muted">VERIFIED: </span>
                <span
                  className={`tabular-nums font-bold ${
                    entry.trust_score === "HIGH"
                      ? "text-t-green"
                      : entry.trust_score === "MEDIUM"
                      ? "text-t-amber"
                      : "text-t-red"
                  }`}
                >
                  {entry.verified_number?.toFixed(4) ?? "N/A"}
                </span>
              </div>
            </div>

            {entry.correction_log.map((c, i) => (
              <div key={i} className="text-[9px] font-mono">
                <span className="text-t-amber font-bold">{c.rule}</span>
                <span className="text-t-muted"> — </span>
                <span className="text-t-secondary">
                  {c.before?.toFixed(4)} → {c.after?.toFixed(4)}
                </span>
                {c.description && (
                  <div className="text-t-muted ml-2 mt-0.5">{c.description}</div>
                )}
              </div>
            ))}

            <button
              onClick={() => onRerun(entry)}
              disabled={rerunning}
              className="mt-2 text-[9px] font-mono font-bold text-t-cyan border border-t-cyan/30 px-2 py-1 rounded hover:bg-t-cyan/5 transition-colors disabled:opacity-50"
            >
              {rerunning ? "RE-RUNNING..." : "↻ RE-RUN WITH CURRENT MODEL"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Stats cards ── */
function StatsRow({ history }: { history: HistoryEntry[] }) {
  const total = history.length;
  const high = history.filter((h) => h.trust_score === "HIGH").length;
  const med = history.filter((h) => h.trust_score === "MEDIUM").length;
  const low = history.filter((h) => h.trust_score === "LOW").length;
  const corrections = history.reduce((s, h) => s + h.correction_log.length, 0);

  return (
    <div className="grid grid-cols-5 gap-2 mb-4">
      {[
        { label: "TOTAL", value: total, color: "text-t-blue" },
        { label: "HIGH", value: high, color: "text-t-green" },
        { label: "MEDIUM", value: med, color: "text-t-amber" },
        { label: "LOW", value: low, color: "text-t-red" },
        { label: "FIXES", value: corrections, color: "text-t-cyan" },
      ].map((s) => (
        <div key={s.label} className="panel p-3 text-center">
          <div className={`text-xl font-bold font-mono ${s.color}`}>{s.value}</div>
          <div className="text-[8px] text-t-muted font-mono uppercase tracking-wider mt-0.5">{s.label}</div>
        </div>
      ))}
    </div>
  );
}

/* ── Main ── */
export default function DashboardPage() {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [filter, setFilter] = useState<TrustFilter>("ALL");
  const [rerunning, setRerunning] = useState(false);

  // Load history from localStorage
  useEffect(() => {
    setHistory(loadHistory());
  }, []);

  const filtered =
    filter === "ALL" ? history : history.filter((h) => h.trust_score === filter);

  const handleRerun = useCallback(
    async (entry: HistoryEntry) => {
      if (!entry.raw_number) return;
      setRerunning(true);
      try {
        const res = await verifyNumber(entry.question, entry.raw_number);
        const newEntry: HistoryEntry = {
          id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
          question: entry.question,
          raw_number: res.raw_number,
          verified_number: res.verified_number,
          trust_score: res.trust_score,
          trust_color: res.trust_color,
          correction_log: res.correction_log,
          display_value: res.display_value,
          timestamp: new Date().toISOString(),
        };
        setHistory((prev) => {
          const updated = [newEntry, ...prev];
          saveHistoryLocal(updated);
          return updated;
        });
      } catch {
        /* silently fail */
      } finally {
        setRerunning(false);
      }
    },
    []
  );

  const handleClearHistory = () => {
    if (confirm("Clear all query history?")) {
      saveHistoryLocal([]);
      setHistory([]);
    }
  };



  return (
    <div className="max-w-4xl mx-auto p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-lg font-bold font-mono text-t-green tracking-wider">
            DVL DASHBOARD
          </h1>
          <p className="text-[10px] font-mono text-t-muted mt-0.5">
            Query History &amp; Analytics — {history.length} queries
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleClearHistory}
            className="text-[9px] font-mono text-t-muted border border-t-border/50 px-2 py-1 rounded hover:text-t-red hover:border-t-red/30 transition-colors"
          >
            CLEAR HISTORY
          </button>
        </div>
      </div>

      {/* Stats */}
      <StatsRow history={history} />

      {/* Filter tabs */}
      <div className="flex border-b border-t-border/50 mb-0">
        {(["ALL", "HIGH", "MEDIUM", "LOW"] as TrustFilter[]).map((f) => {
          const count =
            f === "ALL"
              ? history.length
              : history.filter((h) => h.trust_score === f).length;
          const activeColor =
            f === "HIGH"
              ? "text-t-green border-t-green"
              : f === "MEDIUM"
              ? "text-t-amber border-t-amber"
              : f === "LOW"
              ? "text-t-red border-t-red"
              : "text-t-cyan border-t-cyan";
          return (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`flex-1 py-2 text-[10px] font-mono font-bold uppercase tracking-wider transition-colors ${
                filter === f
                  ? `${activeColor} border-b bg-white/[0.02]`
                  : "text-t-muted hover:text-t-secondary border-b border-transparent"
              }`}
            >
              {f} ({count})
            </button>
          );
        })}
      </div>

      {/* History list */}
      <div className="panel">
        {filtered.length === 0 ? (
          <div className="px-4 py-12 text-center">
            <div className="text-t-muted text-[11px] font-mono mb-2">
              {history.length === 0
                ? "No queries yet — use the Terminal to run DVL verifications"
                : `No ${filter} trust queries found`}
            </div>
            {history.length === 0 && (
              <a
                href="/"
                className="text-[10px] font-mono text-t-cyan border border-t-cyan/30 px-3 py-1.5 rounded hover:bg-t-cyan/5 transition-colors"
              >
                → GO TO TERMINAL
              </a>
            )}
          </div>
        ) : (
          filtered.slice(0, 20).map((entry) => (
            <HistoryRow
              key={entry.id}
              entry={entry}
              onRerun={handleRerun}
              rerunning={rerunning}
            />
          ))
        )}
      </div>

      {/* Footer */}
      <div className="mt-4 text-center text-[9px] font-mono text-t-muted">
        History stored locally in browser
      </div>
    </div>
  );
}
