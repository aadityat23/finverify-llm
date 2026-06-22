"use client";

import React, { useEffect, useState, useRef } from "react";
import { getAllQuotes, isFinnhubConfigured, type FinnhubQuote } from "@/lib/market";
import type { MarketQuote } from "@/lib/api";

/**
 * TickerBar — Scrolling marquee showing live stock quotes.
 * Uses Finnhub for real data when API key is configured.
 * Falls back to static data if Finnhub key is missing or API fails.
 */

const TICKER_SYMBOLS = ["AAPL", "TSLA", "JPM", "NVDA", "MSFT", "GS"];

const FALLBACK_TICKERS: MarketQuote[] = [
  { symbol: "AAPL", price: 192.34, prev_close: 190.13, change: 2.21, change_pct: 1.16, volume: 0, market_cap: 0 },
  { symbol: "TSLA", price: 174.82, prev_close: 176.22, change: -1.40, change_pct: -0.79, volume: 0, market_cap: 0 },
  { symbol: "JPM", price: 198.45, prev_close: 197.50, change: 0.95, change_pct: 0.48, volume: 0, market_cap: 0 },
  { symbol: "NVDA", price: 877.35, prev_close: 857.60, change: 19.75, change_pct: 2.30, volume: 0, market_cap: 0 },
  { symbol: "MSFT", price: 422.86, prev_close: 420.72, change: 2.14, change_pct: 0.51, volume: 0, market_cap: 0 },
  { symbol: "GS", price: 467.20, prev_close: 465.80, change: 1.40, change_pct: 0.30, volume: 0, market_cap: 0 },
];

interface TickerItem {
  symbol: string;
  price: number;
  change: number;
  changePct: number;
}

function finnhubToTicker(q: FinnhubQuote): TickerItem {
  return { symbol: q.symbol, price: q.price, change: q.change, changePct: q.changePct };
}

function fallbackToTicker(q: MarketQuote): TickerItem {
  return { symbol: q.symbol, price: q.price, change: q.change, changePct: q.change_pct };
}

export default function TickerBar() {
  const [tickers, setTickers] = useState<TickerItem[]>(FALLBACK_TICKERS.map(fallbackToTicker));
  const [isLive, setIsLive] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Fetch real quotes from Finnhub
  useEffect(() => {
    if (!isFinnhubConfigured()) return;

    const fetchQuotes = async () => {
      try {
        const quotes = await getAllQuotes(TICKER_SYMBOLS);
        if (quotes.length > 0) {
          setTickers(quotes.map(finnhubToTicker));
          setIsLive(true);
        }
      } catch {
        // Keep existing data
      }
    };

    fetchQuotes();
    // Refresh every 30s (Finnhub free tier rate limit)
    const interval = setInterval(fetchQuotes, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-[32px] flex items-center bg-[#0c0c0c] border-b border-t-border/50 overflow-hidden relative">
      {/* Data source indicator */}
      <div className="flex items-center gap-1.5 pl-3 pr-3 border-r border-t-border/30 shrink-0">
        <span
          className={`w-[5px] h-[5px] rounded-full ${isLive ? "bg-t-green animate-glow-pulse" : "bg-t-muted"}`}
        />
        <span className={`text-[8px] font-mono font-bold ${isLive ? "text-t-green" : "text-t-muted"}`}>
          {isLive ? "LIVE" : "STATIC"}
        </span>
      </div>

      {/* Scrolling marquee */}
      <div className="flex-1 overflow-hidden" ref={scrollRef}>
        <div className="ticker-scroll flex items-center gap-5 whitespace-nowrap px-4">
          {/* Render items twice for seamless scroll loop */}
          {[...tickers, ...tickers].map((item, i) => {
            const isUp = item.changePct >= 0;
            const arrow = isUp ? "▲" : "▼";
            const color = isUp ? "text-t-green" : "text-t-red";
            return (
              <span key={`${item.symbol}-${i}`} className="flex items-center gap-1.5 text-[10px] font-mono tracking-wide">
                <span className="text-t-muted">{item.symbol}</span>
                <span className="text-t-primary">
                  ${item.price >= 1000 ? item.price.toLocaleString(undefined, { maximumFractionDigits: 2 }) : item.price.toFixed(2)}
                </span>
                <span className={color}>
                  {arrow} {Math.abs(item.changePct).toFixed(2)}%
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
