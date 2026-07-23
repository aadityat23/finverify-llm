"use client";
import React, { useState, useCallback } from "react";
import QueryInput from "@/components/QueryInput";
import TerminalPanel from "@/components/TerminalPanel";
import VerificationLog from "@/components/VerificationLog";
import TrustScore from "@/components/TrustScore";
import QueryInterpretation from "@/components/QueryInterpretation";
import DVLReport from "@/components/DVLReport";
import { verifyNumber, queryLLM, type QueryResponse } from "@/lib/api";
import { useConnection } from "@/lib/connection";
import { addToHistory } from "@/lib/history";



/* ── Client-side DVL fallback ── */
const RATIO_KW = ["ratio","percentage","percent","rate","margin","return","yield","growth","change","increase","decrease","loss"];

/* Advisory keyword detection */
const ADVISORY_KW = ["should i", "recommend", "advice", "invest in", "buy or sell", "good investment", "better stock", "where should"];

function isAdvisoryQuery(q: string): boolean {
  return ADVISORY_KW.some((kw) => q.toLowerCase().includes(kw));
}

/*
 * Client-side DVL fallback — mirrors backend full_verify() for demo/offline use.
 *
 * KNOWN DRIFT vs backend dvl.py full_verify():
 *   - Missing: sign correction (requires ground truth → also skipped on backend without `actual`)
 *   - Missing: magnitude correction (backend fires heuristic for ratio Qs with extreme values)
 *   - Trust scoring diverged: clientDVL assigns fixed MEDIUM for any scale correction,
 *     while backend uses delta-based compute_trust() which would assign LOW for ~100× changes.
 *   - This is acceptable since clientDVL only runs for known demo cases with hardcoded numbers.
 *   - If a custom-query fallback path is ever reintroduced, these should be synchronized.
 */
function clientDVL(question: string, raw: number): QueryResponse {
  const isRatio = RATIO_KW.some((kw) => question.toLowerCase().includes(kw));
  let value = raw;
  const log: QueryResponse["correction_log"] = [];

  // Scale correction (mirrors backend v1.2 logic)
  if (isRatio) {
    if (Math.abs(value) > 100) {
      const c = value / 100;
      log.push({ rule: "scale_div100", before: value, after: c, description: "Percentage-decimal confusion: value interpreted as percentage, corrected to decimal" });
      value = c;
    } else if (Math.abs(value) < 1) {
      const c = value * 100;
      log.push({ rule: "scale_mul100", before: value, after: c, description: "Percentage-decimal confusion: value interpreted as decimal, corrected to percentage" });
      value = c;
    }
    // 1-100: AMBIGUOUS — no auto-correct
  }

  // Trust scoring — scale corrections are expected and should be MEDIUM
  let trust: string;
  let trustColor: string;
  if (log.length === 0) { trust = "HIGH"; trustColor = "#00ff88"; }
  else {
    const isScale = log.some((l) => l.rule.startsWith("scale_"));
    if (isScale) { trust = "MEDIUM"; trustColor = "#fbbf24"; }
    else {
      const delta = Math.abs(value - raw) / (Math.abs(raw) + 1e-10);
      if (delta < 0.05) { trust = "HIGH"; trustColor = "#00ff88"; }
      else if (delta < 0.5) { trust = "MEDIUM"; trustColor = "#fbbf24"; }
      else { trust = "LOW"; trustColor = "#f87171"; }
    }
  }

  const display = isRatio ? `${value.toFixed(2)}%` : Math.abs(value) > 1e6 ? value.toLocaleString() : value.toFixed(4);
  return {
    question, raw_text: `LLM output: ${raw}`, raw_number: raw,
    verified_number: value, correction_log: log, trust_score: trust,
    trust_color: trustColor, display_value: display, mode: "numerical", verified: true,
  };
}

/* ── Demo cases ── */
const DEMO_CASES = [
  { question: "What was the YoY operating margin change?", raw_number: 0.1240 },
  { question: "What was the percentage decrease in HTM securities?", raw_number: -34.11 },
  { question: "What was the increase in Class A shares outstanding?", raw_number: 104.0 },
];

type RightTab = "session" | "errors" | "stats";

// Known demo/sample questions → use /verify (DVL only, fast)
const DEMO_NUMS: Record<string, number> = {
  "YoY operating margin change?": 0.1240,
  "CET1 ratio Q4 2022?": 10.935,
  "Net income increase YoY?": 1250000,
  "Revenue growth rate?": 8.14,
  "HTM securities decrease?": -34.11,
  "Class A shares outstanding change?": 104.0,
};

/* ── DVL Explainer (empty state) ── */
function DVLExplainer() {
  return (
    <div className="panel">
      <div className="panel-header">
        <span className="label text-t-cyan">HOW DVL WORKS</span>
        <span className="text-[9px] text-t-muted font-mono">3 DETERMINISTIC RULES</span>
      </div>
      <div className="px-3 py-3 space-y-3">
        <div className="text-[10px] text-t-secondary font-mono leading-relaxed mb-3">
          The Deterministic Verification Layer applies ordered rules to catch formatting-level errors in LLM numerical outputs.
        </div>
        <div className="flex flex-wrap gap-2">
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-t-green/5 border border-t-green/15 rounded text-[10px] font-mono">
            <span className="text-t-green font-bold">SCALE</span>
            <span className="text-t-muted">0.12</span>
            <span className="text-t-green">→</span>
            <span className="text-t-primary">12%</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-t-amber/5 border border-t-amber/15 rounded text-[10px] font-mono">
            <span className="text-t-amber font-bold">SIGN</span>
            <span className="text-t-muted">-0.34</span>
            <span className="text-t-amber">→</span>
            <span className="text-t-primary">+0.34</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-t-blue/5 border border-t-blue/15 rounded text-[10px] font-mono">
            <span className="text-t-blue font-bold">MAGNITUDE</span>
            <span className="text-t-muted">104</span>
            <span className="text-t-blue">→</span>
            <span className="text-t-primary">1040</span>
          </div>
        </div>
        <div className="text-[9px] text-t-muted font-mono mt-2">
          Run the demo or type a query to see DVL in action.
        </div>
      </div>
    </div>
  );
}

/* ── Advisory query error state ── */
function AdvisoryState({ onSelect }: { onSelect: (q: string) => void }) {
  const suggestions = [
    "What was Tesla's profit margin?",
    "What was Apple's YoY revenue growth?",
    "What was JPMorgan's CET1 ratio?",
  ];
  return (
    <div className="panel border-l-2 border-t-amber">
      <div className="px-3 py-3">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-t-amber text-[12px]">⚠</span>
          <span className="text-[11px] font-mono font-bold text-t-amber">ADVISORY QUERY DETECTED</span>
        </div>
        <div className="text-[10px] font-mono text-t-secondary mb-3 leading-relaxed">
          This system verifies <span className="text-t-green">numerical</span> financial outputs, not investment recommendations.
          Advisory queries cannot be DVL-verified.
        </div>
        <div className="text-[9px] font-mono text-t-muted mb-1.5 uppercase tracking-wider">TRY THESE INSTEAD:</div>
        <div className="flex flex-wrap gap-1">
          {suggestions.map((q) => (
            <button
              key={q}
              onClick={() => onSelect(q)}
              className="text-[9px] font-mono px-2 py-1 rounded border border-t-cyan/20 text-t-cyan hover:bg-t-cyan/5 transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function HomePage() {
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [history, setHistory] = useState<QueryResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [demoStatus, setDemoStatus] = useState<string | null>(null);
  const [rightTab, setRightTab] = useState<RightTab>("session");
  const [failureCaseOpen, setFailureCaseOpen] = useState(false);
  const [advisoryDetected, setAdvisoryDetected] = useState(false);
  const { backendOnline } = useConnection();

  const handleSubmit = useCallback(async (question: string) => {
    setAdvisoryDetected(false);

    // Check for advisory queries
    if (isAdvisoryQuery(question)) {
      setAdvisoryDetected(true);
      return;
    }

    setIsLoading(true);
    setError(null);
    setLoadingMessage(null);
    try {
      let res: QueryResponse;
      const knownDemo = DEMO_NUMS[question];

      if (knownDemo !== undefined) {
        // Known sample query → /verify (DVL only, no LLM cold start)
        try {
          if (backendOnline) {
            res = await verifyNumber(question, knownDemo);
          } else {
            res = clientDVL(question, knownDemo);
          }
        } catch {
          res = clientDVL(question, knownDemo);
        }
      } else if (backendOnline) {
        // User-typed query + backend online → /query (LLM + DVL)
        setLoadingMessage("QUERYING LLM MODEL — this may take 15-30s on first request (cold start)");
        try {
          res = await queryLLM(question);
          // Check if backend returned an LLM-offline response
          if (res.mode === "dvl_only" && res.trust_score === "N/A") {
            setError("LLM is currently unavailable. The backend is online but the LLM inference token is not configured. Please try again later.");
            setIsLoading(false);
            setLoadingMessage(null);
            return;
          }
        } catch {
          // LLM call failed → show clean error, don't fake a result
          setError("LLM is currently unavailable. Please try again shortly.");
          setIsLoading(false);
          setLoadingMessage(null);
          return;
        }
      } else {
        // Backend offline → show clean error for custom queries
        setError("Backend is offline. Custom queries require a connection to the FinVerify API. Try a demo query instead.");
        setIsLoading(false);
        setLoadingMessage(null);
        return;
      }
      setResult(res);
      setHistory((h) => [res, ...h].slice(0, 20));
      // Persist to dashboard history (localStorage)
      try { addToHistory(res); } catch {}
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setIsLoading(false);
      setLoadingMessage(null);
    }
  }, [backendOnline]);

  const handleRunDemo = useCallback(async () => {
    setAdvisoryDetected(false);
    setIsLoading(true);
    setError(null);
    for (let i = 0; i < DEMO_CASES.length; i++) {
      setDemoStatus(`DEMO ${i + 1}/${DEMO_CASES.length}`);
      const c = DEMO_CASES[i];
      try {
        let res: QueryResponse;
        if (backendOnline) {
          try {
            res = await verifyNumber(c.question, c.raw_number);
          } catch {
            res = clientDVL(c.question, c.raw_number);
          }
        } else {
          res = clientDVL(c.question, c.raw_number);
        }
        setResult(res);
        setHistory((h) => [res, ...h].slice(0, 20));
      } catch { /* ignore */ }
      if (i < DEMO_CASES.length - 1) {
        await new Promise((r) => setTimeout(r, 2000));
      }
    }
    setDemoStatus("COMPLETE");
    setTimeout(() => setDemoStatus(null), 2000);
    setIsLoading(false);
  }, [backendOnline]);

  const restoreResult = (r: QueryResponse) => setResult(r);

  /* Session stats */
  const totalCorrections = history.reduce((s, r) => s + r.correction_log.length, 0);
  const highTrust = history.filter((r) => r.trust_score === "HIGH").length;
  const avgTrust = history.length > 0 ? Math.round((highTrust / history.length) * 100) : 0;
  const errorEntries = history.filter((r) => r.correction_log.length > 0);

  const hasResult = result !== null;

  return (
    <>
    {/* ── Hero Section ── */}
    <section id="hero" className="px-4 pt-4 pb-2 max-w-[1800px] mx-auto w-full">
      <div className="panel p-5 relative overflow-hidden" style={{ borderColor: "rgba(0,255,136,0.12)" }}>
        <div className="absolute inset-0 bg-gradient-to-br from-t-green/[0.03] via-transparent to-t-cyan/[0.02] pointer-events-none" />
        <div className="relative z-10">
          <h1 className="text-[15px] font-mono font-bold text-t-green tracking-wider mb-2">
            FINVERIFY — DETERMINISTIC VERIFICATION LAYER
          </h1>
          <p className="text-[11px] font-mono text-t-secondary leading-relaxed max-w-2xl mb-1.5">
            Post-inference verification for financial LLM outputs — catches scale, sign,
            and magnitude errors before they reach production.
          </p>
          <p className="text-[10px] font-mono text-t-muted mb-4">
            <span className="text-t-green">●</span> Numerical formatting corrections
            <span className="mx-2 text-t-border">|</span>
            <span className="text-t-cyan">●</span> SEC EDGAR fundamentals
            <span className="mx-2 text-t-border">|</span>
            <span className="text-t-amber">●</span> Earnings transcript verification
          </p>
          <a
            id="cta-early-access"
            href="mailto:aaditya@finverify.dev?subject=Early%20Access%20Request"
            className="inline-flex items-center gap-2 px-4 py-2 text-[10px] font-mono font-bold uppercase tracking-wider text-t-green border border-t-green/30 rounded hover:bg-t-green/5 hover:border-t-green/50 transition-all"
          >
            REQUEST EARLY ACCESS →
          </a>
        </div>
      </div>
    </section>

    {/* ── Capabilities Section ── */}
    <section id="capabilities" className="px-4 pb-2 max-w-[1800px] mx-auto w-full">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        {/* DVL Numeric Correction */}
        <div className="panel p-4 border-l-2 border-t-green">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-t-green text-[11px]">✓</span>
            <span className="text-[10px] font-mono font-bold text-t-green uppercase tracking-wider">DVL Numeric Correction</span>
          </div>
          <p className="text-[10px] font-mono text-t-secondary leading-relaxed mb-2">
            Three-stage deterministic pipeline: scale correction, sign correction, magnitude correction.
            42× accuracy improvement on correctable errors (FinQA, n=873).
          </p>
          <span className="text-[9px] font-mono text-t-muted">↓ Demo below</span>
        </div>
        {/* SEC EDGAR Fundamentals */}
        <div className="panel p-4 border-l-2 border-t-cyan">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-t-cyan text-[11px]">✓</span>
            <span className="text-[10px] font-mono font-bold text-t-cyan uppercase tracking-wider">SEC EDGAR Fundamentals</span>
          </div>
          <p className="text-[10px] font-mono text-t-secondary leading-relaxed mb-2">
            Pull DVL-verified financial metrics directly from SEC filings.
            Revenue, margins, EPS — sourced and corrected automatically.
          </p>
          <a href="/metrics" className="text-[9px] font-mono text-t-cyan hover:underline">→ View on Research page</a>
        </div>
        {/* Earnings Transcript Verification */}
        <div className="panel p-4 border-l-2 border-t-amber">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-t-amber text-[11px]">✓</span>
            <span className="text-[10px] font-mono font-bold text-t-amber uppercase tracking-wider">Earnings Verification</span>
          </div>
          <p className="text-[10px] font-mono text-t-secondary leading-relaxed mb-2">
            Verify numeric claims in CEO/CFO earnings call transcripts.
            Red-flag analysis catches ambiguous or inconsistent figures.
          </p>
          <a href="/metrics" className="text-[9px] font-mono text-t-amber hover:underline">→ View on Research page</a>
        </div>
      </div>
    </section>

    <div className="flex-1 grid grid-cols-1 lg:grid-cols-[32%_42%_26%] gap-2 p-2 max-w-[1800px] mx-auto w-full h-[calc(100vh-73px)]">
      {/* ── Left: Query Input ── */}
      <div className="flex flex-col min-h-0">
        <QueryInput
          onSubmit={handleSubmit}
          onRunDemo={handleRunDemo}
          isLoading={isLoading}
          demoStatus={demoStatus}
        />
      </div>

      {/* ── Center: Results Stack ── */}
      <div className="flex flex-col gap-2 min-h-0 overflow-y-auto">
        {/* Advisory error state */}
        {advisoryDetected && (
          <AdvisoryState onSelect={(q) => { setAdvisoryDetected(false); handleSubmit(q); }} />
        )}

        {/* Query interpretation strip — only when result exists */}
        {hasResult && !advisoryDetected && (
          <QueryInterpretation result={result} />
        )}

        {/* DVL explainer (empty state) — only when no result yet */}
        {!hasResult && !isLoading && !advisoryDetected && (
          <DVLExplainer />
        )}

        {/* Raw output */}
        <TerminalPanel result={result} isLoading={isLoading} loadingMessage={loadingMessage} />

        {/* DVL Correction Log */}
        <VerificationLog
          correctionLog={result?.correction_log ?? []}
          rawNumber={result?.raw_number ?? null}
          question={result?.question ?? ""}
          isLoading={isLoading}
        />

        {/* Verified output + trust */}
        <TrustScore result={result} />

        {/* Export Report button */}
        {history.length > 0 && (
          <div className="flex justify-end">
            <DVLReport entries={history} />
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="panel p-2 border-l-2 border-t-red">
            <div className="text-t-red text-[10px] font-mono">{error}</div>
          </div>
        )}

        {/* Failure Case Toggle */}
        <div className="panel">
          <button
            onClick={() => setFailureCaseOpen(!failureCaseOpen)}
            className="w-full panel-header hover:bg-white/[0.02] transition-colors cursor-pointer"
          >
            <span className="label text-t-red">
              {failureCaseOpen ? "▼" : "▶"} VIEW REASONING FAILURE CASE — DVL CANNOT FIX
            </span>
            <span className="text-[9px] text-t-muted font-mono">73.1% of errors</span>
          </button>
          {failureCaseOpen && (
            <div className="px-3 py-2.5 border-l-2 border-t-red bg-[#110808]">
              <div className="text-[10px] font-mono text-t-amber font-bold mb-2">
                ⚠ REASONING ERROR — UNRECOVERABLE
              </div>
              <div className="space-y-1 text-[10px] font-mono">
                <div className="flex gap-2">
                  <span className="text-t-muted w-[70px] shrink-0">QUERY:</span>
                  <span className="text-t-secondary">&quot;What was JPMorgan&apos;s CET1 ratio in 2008?&quot;</span>
                </div>
                <div className="flex gap-2">
                  <span className="text-t-muted w-[70px] shrink-0">ACTUAL:</span>
                  <span className="text-t-green">0.10935</span>
                </div>
                <div className="flex gap-2">
                  <span className="text-t-muted w-[70px] shrink-0">PREDICTED:</span>
                  <span className="text-t-red">0.07004</span>
                </div>
                <div className="flex gap-2">
                  <span className="text-t-muted w-[70px] shrink-0">DVL OUT:</span>
                  <span className="text-t-primary">0.07004 <span className="text-t-muted">(unchanged)</span></span>
                </div>
                <div className="mt-2 pt-2 border-t border-t-border/50">
                  <div className="text-t-muted mb-1">WHY DVL FAILED:</div>
                  <div className="text-t-secondary leading-relaxed">
                    Model identified correct table row but used wrong denominator
                    (total assets instead of risk-weighted assets). This is a
                    <span className="text-t-red font-bold"> reasoning error</span> —
                    DVL only corrects formatting-level errors (scale, sign, magnitude).
                  </div>
                  <div className="mt-1.5 text-t-amber">
                    Error type: REASONING (73.1% of remaining failures)
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* DVL Scope Limitations — always visible */}
        <div className="panel border-t-border/60">
          <div className="panel-header" style={{ borderBottomColor: "rgba(30,30,30,0.5)" }}>
            <span className="label text-t-muted">DVL SCOPE LIMITATIONS</span>
          </div>
          <div className="px-3 py-2.5 space-y-1.5 text-[10px] font-mono">
            <div className="flex items-start gap-2">
              <span className="text-t-green shrink-0">✓</span>
              <span className="text-t-secondary">
                <span className="text-t-muted">Corrects:</span> scale errors, sign errors, magnitude errors (formatting-level)
              </span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-t-red shrink-0">✗</span>
              <span className="text-t-secondary">
                <span className="text-t-muted">Cannot fix:</span> multi-step reasoning errors{" "}
                <span className="text-t-muted">(73.1% of remaining failures)</span>
              </span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-t-amber shrink-0">⚠</span>
              <span className="text-t-secondary">
                <span className="text-t-muted">When trust is</span>{" "}
                <span className="text-t-amber">MEDIUM</span>/<span className="text-t-red">LOW</span>:{" "}
                independently verify the underlying calculation
              </span>
            </div>
            {/* Enhanced key insight — surfaced from ErrorTaxonomy */}
            <div className="mt-2 pt-2 border-t border-t-border/30">
              <div className="text-[9px] font-mono text-t-secondary leading-relaxed">
                <span className="text-t-red font-bold">73.1%</span> of LLM numerical errors are
                multi-step reasoning failures that DVL cannot correct —
                only <span className="text-t-green font-bold">26.9%</span> are formatting-level
                errors (scale, sign, magnitude) where DVL achieves{" "}
                <span className="text-t-green">42× accuracy improvement on correctable errors</span>.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Right: Tabbed Panel ── */}
      <div className="flex flex-col min-h-0">
        <div className="panel flex-1 flex flex-col min-h-0">
          {/* Tab headers */}
          <div className="flex border-b border-t-border">
            {(["session", "errors", "stats"] as RightTab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setRightTab(tab)}
                className={`flex-1 py-1.5 text-[10px] font-mono font-bold uppercase tracking-wider transition-colors ${
                  rightTab === tab
                    ? "text-t-green border-b border-t-green bg-white/[0.02]"
                    : "text-t-muted hover:text-t-secondary"
                }`}
              >
                {tab}
                {tab === "errors" && errorEntries.length > 0 && (
                  <span className="ml-1 text-t-amber">({errorEntries.length})</span>
                )}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto p-2">
            {/* SESSION tab */}
            {rightTab === "session" && (
              <div className="space-y-0.5">
                {history.length === 0 && (
                  <div className="text-t-muted text-[10px] font-mono text-center py-6">
                    No queries yet — run the demo to get started
                  </div>
                )}
                {history.map((h, i) => {
                  const dotColor = h.trust_score === "HIGH" ? "bg-t-green" : h.trust_score === "MEDIUM" ? "bg-t-amber" : "bg-t-red";
                  return (
                    <button
                      key={i}
                      onClick={() => restoreResult(h)}
                      className="w-full text-left px-2 py-1.5 rounded hover:bg-white/[0.02] transition-colors flex items-center gap-2"
                    >
                      <span className={`w-[5px] h-[5px] rounded-full shrink-0 ${dotColor}`} />
                      <span className="text-[9px] text-t-secondary font-mono truncate flex-1">
                        {h.question.length > 35 ? h.question.slice(0, 35) + "..." : h.question}
                      </span>
                      <span className="text-[9px] text-t-primary font-mono shrink-0">
                        {h.display_value}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}

            {/* ERRORS tab */}
            {rightTab === "errors" && (
              <div className="space-y-0.5">
                {errorEntries.length === 0 && (
                  <div className="text-t-muted text-[10px] font-mono text-center py-6">
                    No corrections applied yet
                  </div>
                )}
                {errorEntries.map((h, i) => (
                  <button
                    key={i}
                    onClick={() => restoreResult(h)}
                    className="w-full text-left px-2 py-1.5 rounded hover:bg-white/[0.02] transition-colors flex items-center gap-2"
                  >
                    <span className="w-[5px] h-[5px] rounded-full shrink-0 bg-t-amber" />
                    <span className="text-[9px] text-t-secondary font-mono truncate flex-1">
                      {h.question.length > 30 ? h.question.slice(0, 30) + "..." : h.question}
                    </span>
                    <span className="text-[9px] text-t-amber font-mono shrink-0">
                      {h.correction_log.length} fix{h.correction_log.length > 1 ? "es" : ""}
                    </span>
                  </button>
                ))}
              </div>
            )}

            {/* STATS tab */}
            {rightTab === "stats" && (
              <div className="space-y-2 pt-2">
                <div className="panel p-3 text-center">
                  <div className="text-xl font-bold font-mono text-t-blue">{history.length}</div>
                  <div className="text-[9px] text-t-muted font-mono uppercase tracking-wider">Queries</div>
                </div>
                <div className="panel p-3 text-center">
                  <div className="text-xl font-bold font-mono text-t-amber">{totalCorrections}</div>
                  <div className="text-[9px] text-t-muted font-mono uppercase tracking-wider">Corrections</div>
                </div>
                <div className="panel p-3 text-center">
                  <div className="text-xl font-bold font-mono text-t-green">{avgTrust}%</div>
                  <div className="text-[9px] text-t-muted font-mono uppercase tracking-wider">Avg Trust</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
    </>
  );
}
