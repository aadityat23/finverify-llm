"use client";

import React, { useEffect, useState } from "react";
import { LineChart, Line, ResponsiveContainer } from "recharts";
import { getAllMetrics, type MetricResult } from "@/lib/api";

/**
 * MetricPanel — 2×2 grid of DVL-verified financial metric cards.
 * Center column of Market Mode (45% width).
 * Each card shows raw → verified value with trust badge + sparkline.
 */

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

/* Format metric values for display */
function formatMetric(value: number | null, metric: string): string {
  if (value === null || value === undefined) return "N/A";
  if (metric === "pe_ratio" || metric === "debt_to_equity") {
    return value.toFixed(2) + "×";
  }
  // Margins, growth, ROE — show as percentage
  if (Math.abs(value) < 1) {
    return (value * 100).toFixed(2) + "%";
  }
  return value.toFixed(2) + "%";
}

interface MetricPanelProps {
  symbol: string;
}

const DISPLAY_METRICS = ["profit_margin", "roe", "pe_ratio", "revenue_growth"];

export default function MetricPanel({ symbol }: MetricPanelProps) {
  const [metrics, setMetrics] = useState<MetricResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    const fetchMetrics = async () => {
      setLoading(true);
      try {
        const data = await getAllMetrics(symbol);
        if (!cancelled) {
          setMetrics(data);
          setLastUpdate(new Date().toLocaleTimeString());
        }
      } catch {
        // Keep existing metrics
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchMetrics();
    // Refresh every 60 seconds (derived metrics don't change as fast)
    const interval = setInterval(fetchMetrics, 60000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [symbol]);

  const displayMetrics = metrics.filter((m) => DISPLAY_METRICS.includes(m.metric));

  return (
    <div className="panel flex flex-col h-full min-h-0">
      {/* Header */}
      <div className="panel-header">
        <span className="label text-t-blue">VERIFIED FINANCIAL METRICS</span>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-t-amber font-mono font-bold">{symbol}</span>
          {loading && (
            <span className="w-[5px] h-[5px] rounded-full bg-t-amber animate-glow-pulse" />
          )}
        </div>
      </div>

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
                      {hasCorrection ? "CORRECTED" : "VERIFIED ✓"}
                    </span>
                  )}
                </div>

                {/* Values */}
                <div className="space-y-1">
                  <div className="flex items-baseline gap-2">
                    <span className="text-[9px] text-t-muted font-mono w-[52px]">RAW:</span>
                    <span className="text-[12px] text-t-secondary font-mono tabular-nums">
                      {m.raw_value !== null ? m.raw_value.toFixed(4) : "N/A"}
                    </span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-[9px] text-t-muted font-mono w-[52px]">VERIFIED:</span>
                    <span className={`text-[14px] font-mono font-bold tabular-nums ${
                      m.trust_score === "HIGH" ? "text-t-green" :
                      m.trust_score === "MEDIUM" ? "text-t-amber" : "text-t-red"
                    }`}>
                      {formatMetric(m.verified_value, m.metric)}
                    </span>
                  </div>
                </div>

                {/* Rule applied */}
                <div className="mt-2 pt-1.5 border-t border-t-border/30">
                  <span className="text-[8px] font-mono text-t-muted">RULE: </span>
                  <span className={`text-[8px] font-mono ${hasCorrection ? "text-t-amber" : "text-t-muted"}`}>
                    {hasCorrection ? m.correction_log[0].rule.toUpperCase() : "NO CORRECTION"}
                  </span>
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

        {/* Debt to Equity — show as a full-width card below */}
        {metrics.filter((m) => m.metric === "debt_to_equity").map((m) => {
          const hasCorrection = m.correction_log.length > 0;
          const trustClass =
            m.trust_score === "HIGH" ? "trust-high" :
            m.trust_score === "MEDIUM" ? "trust-medium" : "trust-low";
          return (
            <div key={m.metric} className="panel p-3 mt-2">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono font-bold text-t-secondary uppercase tracking-wider">
                    {m.label}
                  </span>
                  <div className="flex items-baseline gap-3 mt-1">
                    <span className="text-[9px] text-t-muted font-mono">RAW: {m.raw_value?.toFixed(2) ?? "N/A"}</span>
                    <span className={`text-[14px] font-mono font-bold tabular-nums ${
                      m.trust_score === "HIGH" ? "text-t-green" : "text-t-amber"
                    }`}>
                      {formatMetric(m.verified_value, m.metric)}
                    </span>
                  </div>
                </div>
                {m.trust_score !== "N/A" && (
                  <span className={`trust-badge text-[8px] py-0.5 px-1.5 ${trustClass}`}>
                    {hasCorrection ? "CORRECTED" : "VERIFIED ✓"}
                  </span>
                )}
              </div>
            </div>
          );
        })}

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
                    <span className="text-t-muted/60 truncate">({log.description})</span>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-1.5 border-t border-t-border/50 flex justify-between text-[9px] font-mono text-t-muted">
        <span>DVL-verified • derived metrics only</span>
        {lastUpdate && <span>Updated {lastUpdate}</span>}
      </div>
    </div>
  );
}
