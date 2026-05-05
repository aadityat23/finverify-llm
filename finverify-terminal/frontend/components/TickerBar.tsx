"use client";

import React, { useEffect, useState, useRef } from "react";
import { createMarketWebSocket, getMarketIndices, type MarketQuote } from "@/lib/api";

/**
 * TickerBar — Scrolling marquee showing live stock quotes + index data.
 * Connects to WebSocket /ws/market for real-time updates.
 * Falls back to static data if backend is unreachable.
 */

const FALLBACK_TICKERS: MarketQuote[] = [
  { symbol: "AAPL", price: 192.34, prev_close: 190.13, change: 2.21, change_pct: 1.16, volume: 0, market_cap: 0 },
  { symbol: "TSLA", price: 174.82, prev_close: 176.22, change: -1.40, change_pct: -0.79, volume: 0, market_cap: 0 },
  { symbol: "JPM", price: 198.45, prev_close: 197.50, change: 0.95, change_pct: 0.48, volume: 0, market_cap: 0 },
  { symbol: "NVDA", price: 877.35, prev_close: 857.60, change: 19.75, change_pct: 2.30, volume: 0, market_cap: 0 },
  { symbol: "MSFT", price: 422.86, prev_close: 420.72, change: 2.14, change_pct: 0.51, volume: 0, market_cap: 0 },
  { symbol: "GS", price: 467.20, prev_close: 465.80, change: 1.40, change_pct: 0.30, volume: 0, market_cap: 0 },
];

const FALLBACK_INDICES: MarketQuote[] = [
  { symbol: "SPY", display_name: "S&P 500", price: 5287.14, prev_close: 5245.00, change: 42.14, change_pct: 0.80, volume: 0, market_cap: 0 },
  { symbol: "QQQ", display_name: "NASDAQ", price: 18431.28, prev_close: 18212.80, change: 218.48, change_pct: 1.20, volume: 0, market_cap: 0 },
  { symbol: "^VIX", display_name: "VIX", price: 14.32, prev_close: 14.38, change: -0.06, change_pct: -0.42, volume: 0, market_cap: 0 },
];

export default function TickerBar() {
  const [quotes, setQuotes] = useState<MarketQuote[]>(FALLBACK_TICKERS);
  const [indices, setIndices] = useState<MarketQuote[]>(FALLBACK_INDICES);
  const [connected, setConnected] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // WebSocket for live quotes
  useEffect(() => {
    const ws = createMarketWebSocket(
      (data) => {
        setQuotes(data);
        setConnected(true);
      },
      () => setConnected(false),
    );
    return () => { ws?.close(); };
  }, []);

  // Fetch indices on mount + every 30s
  useEffect(() => {
    const fetchIndices = async () => {
      try {
        const data = await getMarketIndices();
        if (data.length > 0) setIndices(data);
      } catch { /* keep fallback */ }
    };
    fetchIndices();
    const interval = setInterval(fetchIndices, 30000);
    return () => clearInterval(interval);
  }, []);

  const allItems = [...indices, ...quotes];

  return (
    <div className="h-[32px] flex items-center bg-[#0c0c0c] border-b border-t-border/50 overflow-hidden relative">
      {/* Connection indicator */}
      <div className="flex items-center gap-1.5 pl-3 pr-3 border-r border-t-border/30 shrink-0">
        <span
          className={`w-[5px] h-[5px] rounded-full ${connected ? "bg-t-green animate-glow-pulse" : "bg-t-muted"}`}
        />
        <span className="text-[9px] font-mono text-t-muted">
          {connected ? "LIVE" : "STATIC"}
        </span>
      </div>

      {/* Scrolling marquee */}
      <div className="flex-1 overflow-hidden" ref={scrollRef}>
        <div className="ticker-scroll flex items-center gap-5 whitespace-nowrap px-4">
          {/* Render items twice for seamless scroll loop */}
          {[...allItems, ...allItems].map((item, i) => {
            const isUp = item.change_pct >= 0;
            const arrow = isUp ? "▲" : "▼";
            const color = isUp ? "text-t-green" : "text-t-red";
            const name = item.display_name || item.symbol;
            return (
              <span key={`${item.symbol}-${i}`} className="flex items-center gap-1.5 text-[10px] font-mono tracking-wide">
                <span className="text-t-muted">{name}</span>
                <span className="text-t-primary">
                  {item.price >= 1000 ? item.price.toLocaleString(undefined, { maximumFractionDigits: 2 }) : item.price.toFixed(2)}
                </span>
                <span className={color}>
                  {arrow} {isUp ? "+" : ""}{item.change_pct.toFixed(1)}%
                </span>
                <span className="text-t-muted/30 mx-1">│</span>
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
}
