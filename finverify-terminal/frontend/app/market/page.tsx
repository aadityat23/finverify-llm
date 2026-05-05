"use client";

import React, { useState, useEffect } from "react";
import Watchlist from "@/components/Watchlist";
import MetricPanel from "@/components/MetricPanel";
import MarketContext from "@/components/MarketContext";
import { createMarketWebSocket, getMarketQuotes, type MarketQuote } from "@/lib/api";

/**
 * Market Mode — Live market data + DVL verification dashboard.
 * 3-column layout: Watchlist (30%) | DVL Analysis (45%) | Market Context (25%)
 */

const DEFAULT_WATCHLIST = ["AAPL", "TSLA", "JPM", "NVDA", "MSFT", "GS"];

const FALLBACK_QUOTES: MarketQuote[] = [
  { symbol: "AAPL", price: 192.34, prev_close: 190.13, change: 2.21, change_pct: 1.16, volume: 58_000_000, market_cap: 2_980_000_000_000 },
  { symbol: "TSLA", price: 174.82, prev_close: 176.22, change: -1.40, change_pct: -0.79, volume: 112_000_000, market_cap: 556_000_000_000 },
  { symbol: "JPM", price: 198.45, prev_close: 197.50, change: 0.95, change_pct: 0.48, volume: 9_200_000, market_cap: 572_000_000_000 },
  { symbol: "NVDA", price: 877.35, prev_close: 857.60, change: 19.75, change_pct: 2.30, volume: 42_000_000, market_cap: 2_160_000_000_000 },
  { symbol: "MSFT", price: 422.86, prev_close: 420.72, change: 2.14, change_pct: 0.51, volume: 22_000_000, market_cap: 3_140_000_000_000 },
  { symbol: "GS", price: 467.20, prev_close: 465.80, change: 1.40, change_pct: 0.30, volume: 2_100_000, market_cap: 155_000_000_000 },
];

export default function MarketPage() {
  const [quotes, setQuotes] = useState<MarketQuote[]>(FALLBACK_QUOTES);
  const [selectedSymbol, setSelectedSymbol] = useState("AAPL");
  const [wsConnected, setWsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(false);

  // Try REST fetch first
  useEffect(() => {
    const fetchInitial = async () => {
      try {
        const data = await getMarketQuotes(DEFAULT_WATCHLIST);
        if (data.length > 0) setQuotes(data);
      } catch {
        // Keep fallback quotes
      }
    };
    fetchInitial();
  }, []);

  // WebSocket for live updates
  useEffect(() => {
    const ws = createMarketWebSocket(
      (data) => {
        setQuotes(data);
        setWsConnected(true);
        setConnectionError(false);
      },
      () => {
        setWsConnected(false);
        setConnectionError(true);
      },
    );

    return () => { ws?.close(); };
  }, []);

  // Symbol tabs for quick switching
  const symbolTabs = DEFAULT_WATCHLIST;

  return (
    <div className="flex flex-col h-[calc(100vh-73px-32px)]">
      {/* Connection error banner */}
      {connectionError && (
        <div className="px-4 py-1.5 bg-t-amber/5 border-b border-t-amber/20 flex items-center gap-2">
          <span className="w-[5px] h-[5px] rounded-full bg-t-amber animate-pulse" />
          <span className="text-[10px] font-mono text-t-amber">
            MARKET DATA UNAVAILABLE — showing last known values
          </span>
        </div>
      )}

      {/* Symbol quick-select tabs */}
      <div className="flex items-center gap-0 px-2 pt-2 pb-1">
        <span className="text-[9px] font-mono text-t-muted uppercase tracking-wider mr-3">
          ANALYZE:
        </span>
        {symbolTabs.map((sym) => (
          <button
            key={sym}
            onClick={() => setSelectedSymbol(sym)}
            className={`
              px-3 py-1 text-[10px] font-mono font-bold uppercase tracking-wider
              transition-all duration-150 border border-t-border/50 -ml-px first:ml-0
              ${selectedSymbol === sym
                ? "bg-t-green/10 text-t-green border-t-green/30 z-10 relative"
                : "text-t-muted hover:text-t-secondary hover:bg-white/[0.02]"
              }
            `}
          >
            {sym}
          </button>
        ))}
        <div className="flex-1" />
        <div className="flex items-center gap-1.5">
          <span className={`w-[5px] h-[5px] rounded-full ${wsConnected ? "bg-t-green animate-glow-pulse" : "bg-t-muted"}`} />
          <span className="text-[9px] font-mono text-t-muted">
            {wsConnected ? "WS CONNECTED" : "POLLING"}
          </span>
        </div>
      </div>

      {/* 3-column layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[30%_45%_25%] gap-2 p-2 min-h-0">
        {/* Left: Watchlist */}
        <Watchlist
          quotes={quotes}
          selectedSymbol={selectedSymbol}
          onSelectSymbol={setSelectedSymbol}
        />

        {/* Center: DVL Analysis */}
        <MetricPanel symbol={selectedSymbol} />

        {/* Right: Market Context */}
        <MarketContext />
      </div>
    </div>
  );
}
