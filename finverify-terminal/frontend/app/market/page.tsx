"use client";

import React, { useState, useEffect, useCallback } from "react";
import Watchlist from "@/components/Watchlist";
import MetricPanel from "@/components/MetricPanel";
import MarketContext from "@/components/MarketContext";
import EarningsVerification from "@/components/EarningsVerification";
import { type MarketQuote } from "@/lib/api";
import { getAllQuotes, isFinnhubConfigured, type FinnhubQuote } from "@/lib/market";

/**
 * Market Mode — Live market data + DVL verification dashboard.
 * 4-panel layout with tabbed center:
 *   Watchlist (25%) | DVL Analysis/Earnings (50%) | Market Context (25%)
 *
 * Uses Finnhub for real stock quotes when API key is configured.
 * Falls back to static demo data otherwise. Never crashes.
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

/* Convert Finnhub quote to the MarketQuote shape used by Watchlist */
function toMarketQuote(fq: FinnhubQuote): MarketQuote {
  return {
    symbol: fq.symbol,
    price: fq.price,
    prev_close: fq.prevClose,
    change: fq.change,
    change_pct: fq.changePct,
    volume: 0,
    market_cap: 0,
  };
}

type CenterTab = "metrics" | "earnings";

export default function MarketPage() {
  const [quotes, setQuotes] = useState<MarketQuote[]>(FALLBACK_QUOTES);
  const [selectedSymbol, setSelectedSymbol] = useState("AAPL");
  const [isLive, setIsLive] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [centerTab, setCenterTab] = useState<CenterTab>("earnings");

  const fetchQuotes = useCallback(async () => {
    if (!isFinnhubConfigured()) {
      setLastUpdated(new Date().toLocaleTimeString("en-US", { hour12: false }));
      return;
    }
    try {
      const data = await getAllQuotes(DEFAULT_WATCHLIST);
      if (data.length > 0) {
        setQuotes(data.map(toMarketQuote));
        setIsLive(true);
      }
    } catch {
      // Keep existing data
    }
    setLastUpdated(new Date().toLocaleTimeString("en-US", { hour12: false }));
  }, []);

  // Fetch on mount + refresh every 30 seconds
  useEffect(() => {
    fetchQuotes();
    const interval = setInterval(fetchQuotes, 30000);
    return () => clearInterval(interval);
  }, [fetchQuotes]);

  // Symbol tabs for quick switching
  const symbolTabs = DEFAULT_WATCHLIST;

  return (
    <div className="flex flex-col h-[calc(100vh-73px-32px)]">
      {/* Demo mode banner */}
      {!isFinnhubConfigured() && (
        <div className="px-4 py-1.5 bg-t-amber/5 border-b border-t-amber/20 flex items-center gap-2">
          <span className="w-[5px] h-[5px] rounded-full bg-t-amber" />
          <span className="text-[10px] font-mono text-t-amber">
            MARKET DATA — DEMO MODE (add FINNHUB_KEY for live data)
          </span>
        </div>
      )}

      {/* Symbol quick-select tabs + center panel toggle */}
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

        {/* Spacer */}
        <div className="flex-1" />

        {/* Center panel toggle */}
        <div className="flex items-center gap-0 mr-3">
          <button
            onClick={() => setCenterTab("earnings")}
            className={`
              px-2.5 py-1 text-[9px] font-mono font-bold uppercase tracking-wider
              transition-all duration-150 border border-t-border/50 rounded-l
              ${centerTab === "earnings"
                ? "bg-t-cyan/10 text-t-cyan border-t-cyan/30"
                : "text-t-muted hover:text-t-secondary hover:bg-white/[0.02]"
              }
            `}
          >
            🚩 EARNINGS
          </button>
          <button
            onClick={() => setCenterTab("metrics")}
            className={`
              px-2.5 py-1 text-[9px] font-mono font-bold uppercase tracking-wider
              transition-all duration-150 border border-t-border/50 rounded-r -ml-px
              ${centerTab === "metrics"
                ? "bg-t-blue/10 text-t-blue border-t-blue/30"
                : "text-t-muted hover:text-t-secondary hover:bg-white/[0.02]"
              }
            `}
          >
            📊 METRICS
          </button>
        </div>

        {/* Live/Demo indicator */}
        <div className="flex items-center gap-1.5">
          <span className={`w-[5px] h-[5px] rounded-full ${isLive ? "bg-t-green animate-glow-pulse" : "bg-t-muted"}`} />
          <span className={`text-[9px] font-mono ${isLive ? "text-t-green" : "text-t-muted"}`}>
            {isLive ? "LIVE DATA" : "DEMO DATA"}
          </span>
          {lastUpdated && (
            <span className="text-[8px] font-mono text-t-muted ml-2">
              UPDATED {lastUpdated}
            </span>
          )}
        </div>
      </div>

      {/* 3-column layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[25%_50%_25%] gap-2 p-2 min-h-0">
        {/* Left: Watchlist */}
        <Watchlist
          quotes={quotes}
          selectedSymbol={selectedSymbol}
          onSelectSymbol={setSelectedSymbol}
          isLive={isLive}
          lastUpdated={lastUpdated}
        />

        {/* Center: DVL Analysis or Earnings Verification */}
        {centerTab === "metrics" ? (
          <MetricPanel symbol={selectedSymbol} />
        ) : (
          <EarningsVerification symbol={selectedSymbol} />
        )}

        {/* Right: Market Context */}
        <MarketContext />
      </div>
    </div>
  );
}
