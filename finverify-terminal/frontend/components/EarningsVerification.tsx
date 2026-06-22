"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  getEarningsVerification,
  getFundamentals,
  type EarningsReport,
  type EarningsClaim,
  type FundamentalsResponse,
  type FundamentalMetric,
} from "@/lib/api";

/**
 * EarningsVerification — The killer demo feature.
 * Shows DVL catching real-world ambiguity in CEO/CFO earnings statements.
 *
 * Layout:
 *   Top: SEC Filing fundamentals with DVL verification
 *   Bottom: Earnings call transcript claims with Red Flag Report
 *
 * Each claim shows:
 *   "CEO said: margin improved 240 basis points"
 *   "DVL: 240 bps = 2.40% — within 1-100 range — AMBIGUOUS — flagged for review"
 *   Trust: MEDIUM [amber]
 */

/* ── Claim type badge colors ── */
const CLAIM_COLORS: Record<string, string> = {
  currency: "text-t-green",
  currency_raw: "text-t-green",
  percentage: "text-t-blue",
  bps: "text-t-amber",
  growth_pct: "text-t-green",
  decline_pct: "text-t-red",
  shares: "text-t-cyan",
  eps: "text-t-green",
  margin: "text-t-blue",
  revenue: "text-t-green",
  ratio: "text-t-amber",
  return_metric: "text-t-blue",
};

const CLAIM_LABELS: Record<string, string> = {
  currency: "CURRENCY",
  currency_raw: "CURRENCY",
  percentage: "PERCENT",
  bps: "BASIS PTS",
  growth_pct: "GROWTH",
  decline_pct: "DECLINE",
  shares: "SHARES",
  eps: "EPS",
  margin: "MARGIN",
  revenue: "REVENUE",
  ratio: "RATIO",
  return_metric: "RETURN",
};

/* ── Trust badge component ── */
function TrustBadge({ trust, color }: { trust: string; color: string }) {
  const cls =
    trust === "HIGH"
      ? "bg-t-green/10 text-t-green border-t-green/20"
      : trust === "MEDIUM"
      ? "bg-t-amber/10 text-t-amber border-t-amber/20"
      : "bg-t-red/10 text-t-red border-t-red/20";
  return (
    <span
      className={`text-[8px] font-mono font-bold px-1.5 py-0.5 rounded border ${cls}`}
    >
      {trust}
    </span>
  );
}

/* ── Fundamentals card ── */
function FundamentalCard({ metric }: { metric: FundamentalMetric }) {
  const isLarge = Math.abs(metric.raw_value) >= 1e6;
  const formatValue = (v: number) => {
    if (Math.abs(v) >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
    if (Math.abs(v) >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
    if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
    if (Math.abs(v) >= 100) return `$${v.toFixed(2)}`;
    return v.toFixed(4);
  };

  const METRIC_LABELS: Record<string, string> = {
    net_income: "NET INCOME",
    revenue: "REVENUE",
    total_assets: "TOTAL ASSETS",
    eps_basic: "EPS (BASIC)",
    eps_diluted: "EPS (DILUTED)",
    operating_income: "OPERATING INCOME",
    gross_profit: "GROSS PROFIT",
    cost_of_revenue: "COST OF REVENUE",
    stockholders_equity: "STOCKHOLDERS' EQUITY",
  };

  return (
    <div className="panel p-2.5 transition-all duration-300 hover:bg-white/[0.02]">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[9px] font-mono font-bold text-t-secondary uppercase tracking-wider">
          {METRIC_LABELS[metric.metric_name] || metric.metric_name.toUpperCase()}
        </span>
        <TrustBadge trust={metric.dvl_trust} color={metric.dvl_color} />
      </div>
      <div className="flex items-baseline gap-3">
        <span
          className={`text-[15px] font-mono font-bold tabular-nums ${
            metric.dvl_trust === "HIGH"
              ? "text-t-green"
              : metric.dvl_trust === "MEDIUM"
              ? "text-t-amber"
              : "text-t-red"
          }`}
        >
          {formatValue(metric.verified_value)}
        </span>
      </div>
      <div className="flex items-center gap-2 mt-1 text-[8px] font-mono text-t-muted">
        <span>{metric.period}</span>
        <span>•</span>
        <span>{metric.filing_date}</span>
        {metric.dvl_rule && (
          <>
            <span>•</span>
            <span className="text-t-amber">{metric.dvl_rule}</span>
          </>
        )}
      </div>
    </div>
  );
}

/* ── Single claim row ── */
function ClaimRow({
  claim,
  index,
}: {
  claim: EarningsClaim;
  index: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const typeColor = CLAIM_COLORS[claim.claim_type] || "text-t-secondary";
  const typeLabel = CLAIM_LABELS[claim.claim_type] || claim.claim_type.toUpperCase();

  return (
    <div
      className={`border-b border-t-border/30 last:border-b-0 transition-all duration-200 ${
        claim.flagged ? "bg-t-amber/[0.02]" : ""
      }`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-3 py-2 hover:bg-white/[0.02] transition-colors cursor-pointer"
      >
        <div className="flex items-start gap-2">
          {/* Flag indicator */}
          <span
            className={`mt-0.5 w-[6px] h-[6px] rounded-full shrink-0 ${
              claim.flagged
                ? claim.trust_score === "LOW"
                  ? "bg-t-red"
                  : "bg-t-amber"
                : "bg-t-green"
            }`}
          />

          {/* Claim content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span
                className={`text-[7px] font-mono font-bold px-1 py-[1px] rounded border border-current/20 ${typeColor}`}
              >
                {typeLabel}
              </span>
              <span className="text-[10px] font-mono text-t-secondary truncate">
                &ldquo;{claim.match}&rdquo;
              </span>
            </div>
            <div className="text-[9px] font-mono text-t-muted truncate">
              {claim.sentence}
            </div>
          </div>

          {/* Trust badge */}
          <div className="shrink-0 flex items-center gap-1.5">
            <TrustBadge trust={claim.trust_score} color={claim.trust_color} />
            <span className="text-[9px] text-t-muted font-mono">
              {expanded ? "▼" : "▶"}
            </span>
          </div>
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-3 pb-2.5 ml-[14px]">
          <div className="panel p-2.5 bg-[#0d0d0d] space-y-1.5">
            {/* DVL Analysis — the key display */}
            <div className="text-[10px] font-mono">
              <span className="text-t-cyan font-bold">DVL: </span>
              <span className="text-t-secondary">{claim.dvl_analysis}</span>
            </div>

            {/* Raw vs Verified */}
            <div className="flex gap-4 text-[9px] font-mono">
              <div>
                <span className="text-t-muted">RAW: </span>
                <span className="text-t-secondary tabular-nums">
                  {typeof claim.raw_value === "number"
                    ? Math.abs(claim.raw_value) >= 1e6
                      ? claim.raw_value.toLocaleString()
                      : claim.raw_value.toFixed(4)
                    : claim.raw_value}
                </span>
              </div>
              <div>
                <span className="text-t-muted">VERIFIED: </span>
                <span
                  className={`tabular-nums font-bold ${
                    claim.trust_score === "HIGH"
                      ? "text-t-green"
                      : claim.trust_score === "MEDIUM"
                      ? "text-t-amber"
                      : "text-t-red"
                  }`}
                >
                  {typeof claim.verified_value === "number"
                    ? Math.abs(claim.verified_value) >= 1e6
                      ? claim.verified_value.toLocaleString()
                      : claim.verified_value.toFixed(4)
                    : claim.verified_value}
                </span>
              </div>
            </div>

            {/* DVL Rule */}
            {claim.dvl_rule && (
              <div className="text-[9px] font-mono">
                <span className="text-t-muted">RULE: </span>
                <span className="text-t-amber">{claim.dvl_rule}</span>
              </div>
            )}

            {/* BPS detail */}
            {claim.bps_original && (
              <div className="text-[9px] font-mono text-t-amber mt-1 p-1.5 bg-t-amber/5 rounded border border-t-amber/10">
                ⚠ {claim.bps_original} basis points = {(claim.bps_original / 100).toFixed(2)}%
                — scale conversion applied at ingestion
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── View toggle ── */
type ViewMode = "flags" | "all";

/* ── Main component ── */
interface EarningsVerificationProps {
  symbol: string;
}

export default function EarningsVerification({
  symbol,
}: EarningsVerificationProps) {
  const [report, setReport] = useState<EarningsReport | null>(null);
  const [fundamentals, setFundamentals] = useState<FundamentalsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [fundsLoading, setFundsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("flags");
  const [showFundamentals, setShowFundamentals] = useState(true);

  // Fetch earnings report
  const fetchReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getEarningsVerification(symbol);
      setReport(data);
    } catch (e) {
      // Client-side fallback for demo mode
      setError(e instanceof Error ? e.message : "Failed to load");
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  // Fetch fundamentals
  const fetchFundamentals = useCallback(async () => {
    setFundsLoading(true);
    try {
      const data = await getFundamentals(symbol);
      setFundamentals(data);
    } catch {
      setFundamentals(null);
    } finally {
      setFundsLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    fetchReport();
    fetchFundamentals();
  }, [fetchReport, fetchFundamentals]);

  const claims = viewMode === "flags" ? (report?.flags ?? []) : (report?.all_claims ?? []);

  return (
    <div className="panel flex flex-col h-full min-h-0">
      {/* ═══ Header ═══ */}
      <div className="panel-header">
        <span className="label text-t-cyan">EARNINGS VERIFICATION</span>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-t-amber font-mono font-bold">
            {symbol}
          </span>
          {report && (
            <span className="text-[8px] font-mono text-t-red bg-t-red/10 px-1.5 py-0.5 rounded border border-t-red/20">
              {report.flagged_count} FLAGS
            </span>
          )}
          {loading && (
            <span className="w-[5px] h-[5px] rounded-full bg-t-cyan animate-glow-pulse" />
          )}
        </div>
      </div>

      {/* ═══ Content ═══ */}
      <div className="flex-1 overflow-y-auto">
        {/* ── SEC Filing Fundamentals ── */}
        {showFundamentals && (
          <div className="border-b border-t-border/50">
            <button
              onClick={() => setShowFundamentals(!showFundamentals)}
              className="w-full px-3 py-1.5 flex items-center justify-between text-[9px] font-mono text-t-muted uppercase tracking-wider hover:bg-white/[0.02] transition-colors"
            >
              <span>
                <span className="text-t-green">■</span> SEC FILING DATA
                {fundamentals && (
                  <span className="text-t-secondary ml-2">
                    {fundamentals.metrics_count} METRICS
                  </span>
                )}
              </span>
              <span>{showFundamentals ? "▼" : "▶"}</span>
            </button>
            {showFundamentals && fundamentals && (
              <div className="px-2 pb-2 grid grid-cols-2 gap-1.5">
                {fundamentals.metrics.slice(0, 6).map((m: FundamentalMetric, i: number) => (
                  <FundamentalCard key={m.metric_name || i} metric={m} />
                ))}
              </div>
            )}
            {showFundamentals && fundsLoading && (
              <div className="px-3 py-4 text-center text-[10px] font-mono text-t-muted animate-pulse">
                Fetching SEC filing data for {symbol}...
              </div>
            )}
          </div>
        )}

        {/* ── Red Flag Report Header ── */}
        {report && (
          <div className="px-3 py-2 border-b border-t-border/50 bg-[#0a0808]">
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono font-bold text-t-red">
                  🚩 RED FLAG REPORT
                </span>
                <span className="text-[9px] font-mono text-t-muted">
                  {report.total_claims} claims analyzed
                </span>
              </div>
              <span
                className={`text-[10px] font-mono font-bold ${
                  report.flag_rate > 30
                    ? "text-t-red"
                    : report.flag_rate > 15
                    ? "text-t-amber"
                    : "text-t-green"
                }`}
              >
                {report.flag_rate}% FLAG RATE
              </span>
            </div>

            {/* Trust breakdown bar */}
            <div className="flex gap-0.5 h-[4px] rounded-full overflow-hidden mb-2">
              {report.trust_breakdown.high > 0 && (
                <div
                  className="bg-t-green rounded-l"
                  style={{
                    width: `${(report.trust_breakdown.high / report.total_claims) * 100}%`,
                  }}
                />
              )}
              {report.trust_breakdown.medium > 0 && (
                <div
                  className="bg-t-amber"
                  style={{
                    width: `${(report.trust_breakdown.medium / report.total_claims) * 100}%`,
                  }}
                />
              )}
              {report.trust_breakdown.low > 0 && (
                <div
                  className="bg-t-red rounded-r"
                  style={{
                    width: `${(report.trust_breakdown.low / report.total_claims) * 100}%`,
                  }}
                />
              )}
            </div>

            {/* Trust stats */}
            <div className="flex gap-3 text-[9px] font-mono">
              <span className="text-t-green">
                ● {report.trust_breakdown.high} HIGH
              </span>
              <span className="text-t-amber">
                ● {report.trust_breakdown.medium} MEDIUM
              </span>
              <span className="text-t-red">
                ● {report.trust_breakdown.low} LOW
              </span>
            </div>
          </div>
        )}

        {/* ── View toggle ── */}
        {report && (
          <div className="flex border-b border-t-border/50">
            <button
              onClick={() => setViewMode("flags")}
              className={`flex-1 py-1.5 text-[9px] font-mono font-bold uppercase tracking-wider transition-colors ${
                viewMode === "flags"
                  ? "text-t-red border-b border-t-red bg-white/[0.02]"
                  : "text-t-muted hover:text-t-secondary"
              }`}
            >
              ⚠ FLAGGED ({report.flagged_count})
            </button>
            <button
              onClick={() => setViewMode("all")}
              className={`flex-1 py-1.5 text-[9px] font-mono font-bold uppercase tracking-wider transition-colors ${
                viewMode === "all"
                  ? "text-t-cyan border-b border-t-cyan bg-white/[0.02]"
                  : "text-t-muted hover:text-t-secondary"
              }`}
            >
              ALL CLAIMS ({report.total_claims})
            </button>
          </div>
        )}

        {/* ── Claims list ── */}
        {claims.length > 0 && (
          <div>
            {claims.map((claim, i) => (
              <ClaimRow key={`${claim.match}-${i}`} claim={claim} index={i} />
            ))}
          </div>
        )}

        {/* Empty / Loading states */}
        {loading && !report && (
          <div className="px-3 py-8 text-center text-[10px] font-mono text-t-muted animate-pulse">
            Analyzing earnings transcript for {symbol}...
            <br />
            <span className="text-[9px] text-t-cyan">
              Running DVL over each numeric claim
            </span>
          </div>
        )}

        {error && !report && (
          <div className="px-3 py-4 text-center text-[10px] font-mono text-t-amber">
            ⚠ {error}
            <br />
            <span className="text-t-muted">
              Backend may be offline — earnings verification requires API
            </span>
          </div>
        )}

        {report && claims.length === 0 && (
          <div className="px-3 py-6 text-center text-[10px] font-mono text-t-muted">
            {viewMode === "flags"
              ? "No flagged claims — all statements passed DVL verification"
              : "No claims extracted from transcript"}
          </div>
        )}
      </div>

      {/* ═══ Footer ═══ */}
      <div className="px-3 py-1.5 border-t border-t-border/50 flex justify-between text-[9px] font-mono text-t-muted">
        <span>
          DVL-verified • {report?.source === "sample_transcript" ? "sample transcript" : "live transcript"}
        </span>
        {report?.generated_at && (
          <span>
            {new Date(report.generated_at).toLocaleTimeString("en-US", {
              hour12: false,
            })}
          </span>
        )}
      </div>
    </div>
  );
}
