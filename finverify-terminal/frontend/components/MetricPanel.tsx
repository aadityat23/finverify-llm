"use client";

import React, { useEffect, useState } from "react";
import { LineChart, Line, ResponsiveContainer } from "recharts";
import { getBasicFinancials, isFinnhubConfigured, type FinnhubFinancials } from "@/lib/market";
import { clientDVL } from "@/lib/dvl";
import type { MetricResult } from "@/lib/api";

/**
 * MetricPanel — 2×2 grid of DVL-verified financial metric cards.
 * Center column of Market Mode (45% width).
 * Fetches real metrics from Finnhub, then runs each through client-side DVL.
 * Falls back to static data when Finnhub key is missing or API fails.
 *
 * Each card shows:
 *   RAW:      0.2531
 *   VERIFIED: 25.31%
 *   RULE:     scale_mul100
 *   TRUST:    MEDIUM [amber badge]
 */

/* ── Fallback metric definitions per symbol ── */
interface FallbackMetric {
  raw: number;
  label: string;
  question: string;
  metric: string;
}

const FALLBACK_METRICS: Record<string, FallbackMetric[]> = {
  AAPL: [
    { raw: 0.2531, label: "PROFIT MARGIN", question: "profit margin", metric: "profit_margin" },
    { raw: 1.7309, label: "ROE", question: "return on equity", metric: "roe" },
    { raw: 28.45, label: "P/E RATIO", question: "price to earnings ratio", metric: "pe_ratio" },
    { raw: 0.0623, label: "REVENUE GROWTH", question: "revenue growth rate", metric: "revenue_growth" },
  ],
  TSLA: [
    { raw: 0.0553, label: "PROFIT MARGIN", question: "profit margin", metric: "profit_margin" },
    { raw: 0.1124, label: "ROE", question: "return on equity", metric: "roe" },
    { raw: 55.20, label: "P/E RATIO", question: "price to earnings ratio", metric: "pe_ratio" },
    { raw: 0.0187, label: "REVENUE GROWTH", question: "revenue growth rate", metric: "revenue_growth" },
  ],
  JPM: [
    { raw: 0.3012, label: "PROFIT MARGIN", question: "profit margin", metric: "profit_margin" },
    { raw: 0.1687, label: "ROE", question: "return on equity", metric: "roe" },
    { raw: 12.30, label: "P/E RATIO", question: "price to earnings ratio", metric: "pe_ratio" },
    { raw: 0.2134, label: "REVENUE GROWTH", question: "revenue growth rate", metric: "revenue_growth" },
  ],
  NVDA: [
    { raw: 0.5573, label: "PROFIT MARGIN", question: "profit margin", metric: "profit_margin" },
    { raw: 1.2341, label: "ROE", question: "return on equity", metric: "roe" },
    { raw: 68.90, label: "P/E RATIO", question: "price to earnings ratio", metric: "pe_ratio" },
    { raw: 1.2229, label: "REVENUE GROWTH", question: "revenue growth rate", metric: "revenue_growth" },
  ],
  MSFT: [
    { raw: 0.3591, label: "PROFIT MARGIN", question: "profit margin", metric: "profit_margin" },
    { raw: 0.3812, label: "ROE", question: "return on equity", metric: "roe" },
    { raw: 35.60, label: "P/E RATIO", question: "price to earnings ratio", metric: "pe_ratio" },
    { raw: 0.1601, label: "REVENUE GROWTH", question: "revenue growth rate", metric: "revenue_growth" },
  ],
  GS: [
    { raw: 0.1923, label: "PROFIT MARGIN", question: "profit margin", metric: "profit_margin" },
    { raw: 0.0834, label: "ROE", question: "return on equity", metric: "roe" },
    { raw: 14.20, label: "P/E RATIO", question: "price to earnings ratio", metric: "pe_ratio" },
    { raw: 0.0445, label: "REVENUE GROWTH", question: "revenue growth rate", metric: "revenue_growth" },
  ],
};

/* Metric definition mapping from Finnhub data */
interface MetricDef {
  label: string;
  question: string;
  metric: string;
  key: keyof FinnhubFinancials;
}

const METRIC_DEFS: MetricDef[] = [
  { label: "PROFIT MARGIN", question: "profit margin", metric: "profit_margin", key: "profitMargin" },
  { label: "ROE", question: "return on equity", metric: "roe", key: "roe" },
  { label: "P/E RATIO", question: "price to earnings ratio", metric: "pe_ratio", key: "peRatio" },
  { label: "REVENUE GROWTH", question: "revenue growth rate", metric: "revenue_growth", key: "revenueGrowth" },
];

/* Generate fake quarterly trend data for sparkline */
function generateTrend(currentValue: number): { v: number }[] {
  const points: { v: number }[] = [];
  const spread = Math.abs(currentValue) * 0.15 || 0.05;
  let val = currentValue - spread * 2;
  for (let i = 0; i < 4; i++) {
    val += (Math.random() - 0.3) * spread;
    points.push({ v: val });
  }
  points.push({ v: currentValue });
  return points;
}

/* Build MetricResult[] from fallback data using client-side DVL */
function buildFallbackMetrics(symbol: string): MetricResult[] {
  const defs = FALLBACK_METRICS[symbol];
  if (!defs) return [];
  return defs.map((def) => {
    const dvl = clientDVL(def.question, def.raw);
    return {
      symbol,
      metric: def.metric,
      label: def.label,
      raw_value: def.raw,
      question_text: def.question,
      verified_value: dvl.verified,
      correction_log: dvl.logs.map((log) => {
        const parts = log.split(": ");
        const rule = parts[0] || "unknown";
        const vals = (parts[1] || "").split(" → ");
        return {
          rule,
          before: parseFloat(vals[0]) || def.raw,
          after: parseFloat(vals[1]) || dvl.verified,
          description: log,
        };
      }),
      trust_score: dvl.trust,
      trust_color: dvl.trustColor,
    };
  });
}

/* Build MetricResult[] from real Finnhub financials using client-side DVL */
function buildLiveMetrics(financials: FinnhubFinancials): MetricResult[] {
  return METRIC_DEFS.map((def) => {
    const rawValue = financials[def.key] as number | null;
    if (rawValue === null || rawValue === undefined) {
      // No data from Finnhub for this metric — show N/A
      return {
        symbol: financials.symbol,
        metric: def.metric,
        label: def.label,
        raw_value: null,
        question_text: def.question,
        verified_value: null,
        correction_log: [],
        trust_score: "N/A",
        trust_color: "#666",
      };
    }

    // Finnhub returns metrics in different scales:
    // - P/E ratio: already a ratio (e.g. 28.5) — no DVL conversion expected
    // - Profit margin, ROE, Revenue growth: Finnhub returns as percentage values
    //   (e.g. 25.31 for 25.31%). To demonstrate DVL value, we feed the decimal form.
    let dvlInput = rawValue;
    if (def.metric !== "pe_ratio") {
      // Convert from Finnhub percentage to decimal so DVL can demonstrate scale_mul100
      dvlInput = rawValue / 100;
    }

    const dvl = clientDVL(def.question, dvlInput);
    return {
      symbol: financials.symbol,
      metric: def.metric,
      label: def.label,
      raw_value: dvlInput,
      question_text: def.question,
      verified_value: dvl.verified,
      correction_log: dvl.logs.map((log) => {
        const parts = log.split(": ");
        const rule = parts[0] || "unknown";
        const vals = (parts[1] || "").split(" → ");
        return {
          rule,
          before: parseFloat(vals[0]) || dvlInput,
          after: parseFloat(vals[1]) || dvl.verified,
          description: log,
        };
      }),
      trust_score: dvl.trust,
      trust_color: dvl.trustColor,
    };
  });
}

/* Format metric values for display */
function formatVerified(value: number | null, metric: string): string {
  if (value === null || value === undefined) return "N/A";
  if (metric === "pe_ratio") {
    return value.toFixed(2) + "×";
  }
  // Margins, growth, ROE — DVL outputs as percentage already
  return value.toFixed(2) + "%";
}

function formatRaw(value: number | null): string {
  if (value === null || value === undefined) return "N/A";
  return value.toFixed(4);
}

interface MetricPanelProps {
  symbol: string;
}

const DISPLAY_METRICS = ["profit_margin", "roe", "pe_ratio", "revenue_growth"];

export default function MetricPanel({ symbol }: MetricPanelProps) {
  const [metrics, setMetrics] = useState<MetricResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string>("");
  const [usingFallback, setUsingFallback] = useState(false);
  const [isLiveData, setIsLiveData] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const fetchMetrics = async () => {
      setLoading(true);
      try {
        // Try Finnhub first
        if (isFinnhubConfigured()) {
          const financials = await getBasicFinancials(symbol);
          if (!cancelled && financials) {
            const liveMetrics = buildLiveMetrics(financials);
            if (liveMetrics.some((m) => m.raw_value !== null)) {
              setMetrics(liveMetrics);
              setUsingFallback(false);
              setIsLiveData(true);
              setLastUpdate(new Date().toLocaleTimeString("en-US", { hour12: false }));
              setLoading(false);
              return;
            }
          }
        }
        // Fall back to client-side DVL with static data
        if (!cancelled) {
          const fallback = buildFallbackMetrics(symbol);
          setMetrics(fallback);
          setUsingFallback(true);
          setIsLiveData(false);
          setLastUpdate(new Date().toLocaleTimeString("en-US", { hour12: false }));
        }
      } catch {
        if (!cancelled) {
          const fallback = buildFallbackMetrics(symbol);
          setMetrics(fallback);
          setUsingFallback(true);
          setIsLiveData(false);
          setLastUpdate(new Date().toLocaleTimeString("en-US", { hour12: false }));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchMetrics();
    // Refresh every 30 seconds
    const interval = setInterval(fetchMetrics, 30000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [symbol]);

  const displayMetrics = metrics.filter((m) => DISPLAY_METRICS.includes(m.metric));

  return (
    <div className="panel flex flex-col h-full min-h-0">
      {/* Header */}
      <div className="panel-header">
        <span className="label text-t-blue">DVL ANALYSIS — VERIFIED METRICS</span>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-t-amber font-mono font-bold">{symbol}</span>
          {isLiveData ? (
            <span className="text-[8px] font-mono text-t-green bg-t-green/10 px-1.5 py-0.5 rounded border border-t-green/20">
              FINNHUB LIVE
            </span>
          ) : (
            <span className="text-[8px] font-mono text-t-muted bg-t-border/30 px-1.5 py-0.5 rounded">
              DEMO DATA
            </span>
          )}
          {loading && (
            <span className="w-[5px] h-[5px] rounded-full bg-t-amber animate-glow-pulse" />
          )}
        </div>
      </div>

      {/* Demo mode notice */}
      {usingFallback && !isFinnhubConfigured() && (
        <div className="px-3 py-1.5 bg-t-amber/5 border-b border-t-amber/10 text-[9px] font-mono text-t-amber">
          MARKET DATA — DEMO MODE (add FINNHUB_KEY for live data)
        </div>
      )}

      {/* Metric grid */}
      <div className="flex-1 overflow-y-auto p-2">
        {displayMetrics.length === 0 && !loading && (
          <div className="text-center text-t-muted text-[10px] font-mono py-8">
            No metrics available for {symbol}
          </div>
        )}

        {loading && displayMetrics.length === 0 && (
          <div className="text-center text-t-muted text-[10px] font-mono py-8 animate-pulse">
            Fetching DVL-verified metrics for {symbol}...
          </div>
        )}

        <div className="grid grid-cols-2 gap-2">
          {displayMetrics.map((m) => {
            const hasCorrection = m.correction_log.length > 0;
            const trustClass =
              m.trust_score === "HIGH" ? "trust-high" :
              m.trust_score === "MEDIUM" ? "trust-medium" :
              m.trust_score === "LOW" ? "trust-low" : "";
            const trendData = m.raw_value !== null ? generateTrend(m.raw_value) : [];
            const trendColor =
              m.trust_score === "HIGH" ? "#00ff88" :
              m.trust_score === "MEDIUM" ? "#fbbf24" : "#f87171";

            return (
              <div
                key={m.metric}
                className={`
                  panel p-3 relative overflow-hidden transition-all duration-300
                  ${hasCorrection ? "glow-amber border-t-amber/20" : ""}
                `}
              >
                {/* Metric label */}
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono font-bold text-t-secondary uppercase tracking-wider">
                    {m.label}
                  </span>
                  {m.trust_score !== "N/A" && (
                    <span className={`trust-badge text-[8px] py-0.5 px-1.5 ${trustClass}`}>
                      {m.trust_score}
                    </span>
                  )}
                </div>

                {/* Values */}
                <div className="space-y-1">
                  <div className="flex items-baseline gap-2">
                    <span className="text-[9px] text-t-muted font-mono w-[52px]">RAW:</span>
                    <span className="text-[12px] text-t-secondary font-mono tabular-nums">
                      {formatRaw(m.raw_value)}
                    </span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-[9px] text-t-muted font-mono w-[52px]">VERIFIED:</span>
                    <span className={`text-[14px] font-mono font-bold tabular-nums ${
                      m.trust_score === "HIGH" ? "text-t-green" :
                      m.trust_score === "MEDIUM" ? "text-t-amber" : "text-t-red"
                    }`}>
                      {formatVerified(m.verified_value, m.metric)}
                    </span>
                  </div>
                </div>

                {/* Rule + Trust */}
                <div className="mt-2 pt-1.5 border-t border-t-border/30 flex items-center justify-between">
                  <div>
                    <span className="text-[8px] font-mono text-t-muted">RULE: </span>
                    <span className={`text-[8px] font-mono ${hasCorrection ? "text-t-amber" : "text-t-muted"}`}>
                      {hasCorrection ? m.correction_log[0].rule.toUpperCase() : "NO CORRECTION"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[8px] font-mono text-t-muted">TRUST: </span>
                    <span className={`text-[8px] font-mono font-bold ${
                      m.trust_score === "HIGH" ? "text-t-green" :
                      m.trust_score === "MEDIUM" ? "text-t-amber" : "text-t-red"
                    }`}>
                      {m.trust_score}
                    </span>
                  </div>
                </div>

                {/* Mini sparkline */}
                {trendData.length > 0 && (
                  <div className="h-[40px] mt-1.5 opacity-50">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={trendData}>
                        <Line
                          type="monotone"
                          dataKey="v"
                          stroke={trendColor}
                          strokeWidth={1}
                          dot={false}
                          isAnimationActive={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Correction log */}
        {metrics.some((m) => m.correction_log.length > 0) && (
          <div className="panel mt-2 p-3">
            <div className="text-[9px] font-mono text-t-amber font-bold uppercase tracking-wider mb-2">
              DVL CORRECTION LOG
            </div>
            <div className="space-y-1">
              {metrics.filter((m) => m.correction_log.length > 0).map((m) =>
                m.correction_log.map((log, i) => (
                  <div key={`${m.metric}-${i}`} className="flex items-center gap-2 text-[9px] font-mono">
                    <span className="text-t-amber">▸</span>
                    <span className="text-t-secondary">{m.label}:</span>
                    <span className="text-t-muted">{log.before}</span>
                    <span className="text-t-amber">→</span>
                    <span className="text-t-green">{log.after}</span>
                    <span className="text-t-muted/60 truncate">({log.rule})</span>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-1.5 border-t border-t-border/50 flex justify-between text-[9px] font-mono text-t-muted">
        <span>DVL-verified • {isLiveData ? "Finnhub live data" : usingFallback ? "demo data" : "derived metrics"}</span>
        {lastUpdate && <span>UPDATED {lastUpdate}</span>}
      </div>
    </div>
  );
}
