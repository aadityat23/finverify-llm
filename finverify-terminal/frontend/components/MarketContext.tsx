"use client";

import React, { useEffect, useState } from "react";
import { getMarketIndices, type MarketQuote } from "@/lib/api";

/**
 * MarketContext — Right column showing index data + sector performance.
 * Right column of Market Mode (25% width).
 * Uses fallback data immediately so it never shows a stuck loading state.
 */

const FALLBACK_INDICES: MarketQuote[] = [
  { symbol: "SPY", display_name: "S&P 500", price: 5287.14, prev_close: 5245.00, change: 42.14, change_pct: 0.80, volume: 0, market_cap: 0 },
  { symbol: "QQQ", display_name: "NASDAQ", price: 18431.28, prev_close: 18212.80, change: 218.48, change_pct: 1.20, volume: 0, market_cap: 0 },
  { symbol: "^VIX", display_name: "VIX", price: 14.32, prev_close: 14.38, change: -0.06, change_pct: -0.42, volume: 0, market_cap: 0 },
];

const SECTORS = [
  { name: "Financials", change: 1.2 },
  { name: "Technology", change: 0.8 },
  { name: "Healthcare", change: -0.3 },
  { name: "Energy", change: 0.5 },
  { name: "Consumer", change: 0.1 },
];

export default function MarketContext() {
  const [indices, setIndices] = useState<MarketQuote[]>(FALLBACK_INDICES);

  useEffect(() => {
    const fetchIndices = async () => {
      try {
        const data = await getMarketIndices();
        if (data.length > 0) setIndices(data);
      } catch {
        // Keep fallback data — no loading state needed
      }
    };
    fetchIndices();
    const interval = setInterval(fetchIndices, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="panel flex flex-col h-full min-h-0">
      {/* Header */}
      <div className="panel-header">
        <span className="label text-t-purple">MARKET CONTEXT</span>
        <span className="text-[9px] text-t-muted font-mono">
          INDICES
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {/* Index cards */}
        <div className="space-y-1.5">
          {indices.map((idx) => {
            const isUp = idx.change_pct >= 0;
            const color = isUp ? "text-t-green" : "text-t-red";
            const bgGlow = isUp ? "glow-green" : "glow-red";
            const name = idx.display_name || idx.symbol;

            return (
              <div key={idx.symbol} className={`panel p-3 ${bgGlow}`}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-mono font-bold text-t-secondary uppercase tracking-wider">
                    {name}
                  </span>
                  <span className={`text-[9px] font-mono font-bold ${color}`}>
                    {isUp ? "▲" : "▼"} {isUp ? "+" : ""}{idx.change_pct.toFixed(1)}%
                  </span>
                </div>
                <div className="flex items-baseline justify-between">
                  <span className="text-[16px] font-mono font-bold text-t-primary tabular-nums">
                    {idx.price >= 1000
                      ? idx.price.toLocaleString(undefined, { maximumFractionDigits: 2 })
                      : idx.price.toFixed(2)}
                  </span>
                  <span className={`text-[10px] font-mono tabular-nums ${color}`}>
                    {isUp ? "+" : ""}{idx.change.toFixed(2)}
                  </span>
                </div>
                {idx.stale && (
                  <div className="text-[8px] text-t-amber font-mono mt-1">⚠ STALE</div>
                )}
              </div>
            );
          })}
        </div>

        {/* Sector Performance */}
        <div className="panel">
          <div className="panel-header">
            <span className="label text-t-cyan">SECTOR PERFORMANCE</span>
          </div>
          <div className="p-2 space-y-0.5">
            {SECTORS.map((sector) => {
              const isUp = sector.change >= 0;
              const color = isUp ? "text-t-green" : "text-t-red";
              const barWidth = Math.min(Math.abs(sector.change) * 40, 100);

              return (
                <div
                  key={sector.name}
                  className="flex items-center gap-2 px-2 py-1.5 text-[10px] font-mono"
                >
                  <span className="text-t-secondary w-[90px] truncate">
                    {sector.name}
                  </span>
                  <div className="flex-1 h-[3px] bg-t-border/50 rounded-full overflow-hidden relative">
                    <div
                      className={`h-full rounded-full ${isUp ? "bg-t-green/60" : "bg-t-red/60"}`}
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                  <span className={`tabular-nums font-semibold w-[45px] text-right ${color}`}>
                    {isUp ? "+" : ""}{sector.change.toFixed(1)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* DVL Info Box */}
        <div className="panel p-3">
          <div className="text-[9px] font-mono text-t-green font-bold uppercase tracking-wider mb-1.5">
            DVL ENGINE STATUS
          </div>
          <div className="space-y-1 text-[9px] font-mono">
            <div className="flex justify-between">
              <span className="text-t-muted">Engine</span>
              <span className="text-t-green">ACTIVE</span>
            </div>
            <div className="flex justify-between">
              <span className="text-t-muted">Pipeline</span>
              <span className="text-t-secondary">Scale → Sign → Magnitude</span>
            </div>
            <div className="flex justify-between">
              <span className="text-t-muted">FinQA Acc.</span>
              <span className="text-t-amber">42.61% (42× base)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-t-muted">Dataset</span>
              <span className="text-t-secondary">n=873</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
