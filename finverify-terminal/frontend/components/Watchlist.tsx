"use client";

import React from "react";
import { LineChart, Line, ResponsiveContainer } from "recharts";
import type { MarketQuote } from "@/lib/api";

/**
 * Watchlist — Live stock watchlist with sparklines.
 * Left column of Market Mode (30% width).
 */

/* ── Sparkline data generator ── */
function generateSparkline(currentPrice: number, changePct: number): { v: number }[] {
  const points: { v: number }[] = [];
  let price = currentPrice / (1 + changePct / 100);
  for (let i = 0; i < 20; i++) {
    price += (Math.random() - 0.48) * (currentPrice * 0.002);
    points.push({ v: price });
  }
  points.push({ v: currentPrice });
  return points;
}

interface WatchlistProps {
  quotes: MarketQuote[];
  selectedSymbol: string;
  onSelectSymbol: (symbol: string) => void;
}

export default function Watchlist({ quotes, selectedSymbol, onSelectSymbol }: WatchlistProps) {
  return (
    <div className="panel flex flex-col h-full min-h-0">
      {/* Header */}
      <div className="panel-header">
        <span className="label text-t-green">WATCHLIST — LIVE</span>
        <span className="text-[9px] text-t-muted font-mono">{quotes.length} SYMBOLS</span>
      </div>

      {/* Column labels */}
      <div className="grid grid-cols-[60px_1fr_72px_72px_56px] gap-1 px-3 py-1.5 text-[9px] font-mono text-t-muted uppercase tracking-wider border-b border-t-border/50">
        <span>SYM</span>
        <span className="text-right">PRICE</span>
        <span className="text-right">CHG</span>
        <span className="text-right">%CHG</span>
        <span className="text-center">TREND</span>
      </div>

      {/* Rows */}
      <div className="flex-1 overflow-y-auto">
        {quotes.map((q) => {
          const isUp = q.change_pct >= 0;
          const color = isUp ? "text-t-green" : "text-t-red";
          const sparkData = generateSparkline(q.price, q.change_pct);
          const isSelected = q.symbol === selectedSymbol;

          return (
            <button
              key={q.symbol}
              onClick={() => onSelectSymbol(q.symbol)}
              className={`
                w-full grid grid-cols-[60px_1fr_72px_72px_56px] gap-1 items-center px-3 py-2
                text-[11px] font-mono transition-all duration-150 border-l-2
                ${isSelected
                  ? "bg-white/[0.04] border-t-green"
                  : "border-transparent hover:bg-white/[0.02]"
                }
              `}
            >
              {/* Symbol */}
              <span className={`font-bold ${isSelected ? "text-t-green" : "text-t-primary"}`}>
                {q.symbol}
              </span>

              {/* Price */}
              <span className="text-right text-t-primary tabular-nums">
                ${q.price >= 1000 ? q.price.toLocaleString(undefined, { maximumFractionDigits: 2 }) : q.price.toFixed(2)}
              </span>

              {/* Change */}
              <span className={`text-right tabular-nums ${color}`}>
                {isUp ? "+" : ""}{q.change.toFixed(2)}
              </span>

              {/* Change % */}
              <span className={`text-right tabular-nums font-semibold ${color}`}>
                {isUp ? "▲" : "▼"} {Math.abs(q.change_pct).toFixed(2)}%
              </span>

              {/* Sparkline */}
              <div className="h-[28px] w-[48px] mx-auto">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={sparkData}>
                    <Line
                      type="monotone"
                      dataKey="v"
                      stroke={isUp ? "#00ff88" : "#f87171"}
                      strokeWidth={1.2}
                      dot={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </button>
          );
        })}
      </div>

      {/* Footer */}
      <div className="px-3 py-1.5 border-t border-t-border/50 flex justify-between text-[9px] font-mono text-t-muted">
        <span>Click symbol for analysis</span>
        <span>
          {quotes.some((q) => q.stale) && (
            <span className="text-t-amber">⚠ STALE DATA</span>
          )}
        </span>
      </div>
    </div>
  );
}
