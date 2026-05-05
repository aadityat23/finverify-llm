"use client";
import React, { useState, useEffect } from "react";
import AblationSection from "@/components/AblationSection";
import ErrorTaxonomy from "@/components/ErrorTaxonomy";

/* ── Animated counter hook ── */
function useCounter(target: number, suffix = "", duration = 1200) {
  const [val, setVal] = useState("0");
  useEffect(() => {
    const start = performance.now();
    const run = (now: number) => {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      const current = target * eased;
      setVal(Number.isInteger(target) ? Math.round(current).toString() : current.toFixed(2));
      if (p < 1) requestAnimationFrame(run);
      else setVal(Number.isInteger(target) ? target.toString() : target.toFixed(2));
    };
    requestAnimationFrame(run);
  }, [target, duration]);
  return val + suffix;
}

/* ── Stat cards data ── */
const STATS = [
  { value: 42.61, suffix: "%", label: "FINAL ACCURACY", sub: "n=873 FinQA dev set", accent: "#00ff88" },
  { value: 42, suffix: "x", label: "IMPROVEMENT", sub: "over unaugmented baseline", accent: "#22d3ee" },
  { value: 54, suffix: "", label: "DVL CORRECTIONS", sub: "parameter-free, zero training cost", accent: "#fbbf24" },
  { value: 0, suffix: "%", label: "EXTRACTION FAILURES", sub: "after QLoRA fine-tuning", accent: "#a78bfa" },
  { value: 73.1, suffix: "%", label: "REASONING ERRORS", sub: "dominant remaining failure mode", accent: "#f87171" },
];

/* ── Robustness table data ── */
const ROBUST = [
  { cond: "Clean data", ft: "38.5%", dvl: "42.6%", drop: "—", benefit: "+4.1pp", highlight: false },
  { cond: "Distractor numbers", ft: "30.6%", dvl: "30.7%", drop: "-7.9pp", benefit: "+0.1pp", highlight: false },
  { cond: "Missing values", ft: "32.1%", dvl: "42.6%", drop: "-6.4pp", benefit: "+10.5pp", highlight: true },
  { cond: "Conflicting signs", ft: "34.1%", dvl: "42.6%", drop: "-4.4pp", benefit: "+8.5pp", highlight: true },
];

function StatCard({ value, suffix, label, sub, accent }: typeof STATS[0]) {
  const display = useCounter(value, suffix);
  return (
    <div className="panel p-4 relative overflow-hidden" style={{ borderTopColor: accent, borderTopWidth: 2 }}>
      <div className="text-2xl font-bold font-mono" style={{ color: accent }}>{display}</div>
      <div className="text-[10px] text-t-secondary font-mono uppercase tracking-wider mt-1">{label}</div>
      <div className="text-[9px] text-t-muted font-mono mt-0.5">{sub}</div>
    </div>
  );
}

export default function MetricsPage() {
  return (
    <div className="max-w-[1400px] mx-auto w-full p-4 space-y-5">

      {/* ══ KEY RESULT BANNER ══ */}
      <div
        className="border-l-4 border-t-amber px-5 py-4 font-mono"
        style={{ background: "rgba(251,191,36,0.08)" }}
      >
        <div className="flex items-start gap-3">
          <span className="text-[11px] font-bold text-t-amber uppercase tracking-widest shrink-0 mt-0.5">
            KEY RESULT
          </span>
          <div className="text-[12px] text-t-primary leading-relaxed">
            Deterministic verification improves numerical accuracy by{" "}
            <span className="text-t-amber font-bold">42×</span>{" "}
            while reasoning-based methods (CoT, RAG) consistently degrade performance.
            This challenges the dominant assumption that scaling up reasoning is the
            primary path to improvement in financial LLMs.
          </div>
        </div>
      </div>

      {/* ══ HEADER ══ */}
      <div className="panel p-6 space-y-3">
        <h1 className="text-xl font-bold text-t-green font-mono tracking-wider">RESEARCH METRICS</h1>
        <p className="text-[13px] text-t-primary font-mono leading-relaxed">
          Modular Verification Outperforms Chain-of-Thought Reasoning in Small Financial LLMs
        </p>
        <p className="text-[11px] text-t-secondary font-mono">
          Aaditya Thokal &middot; Universal College of Engineering &middot; FinNLP @ EMNLP 2026 (Submitted)
        </p>
        <div className="flex gap-3 pt-1">
          {[
            { label: "HuggingFace Model", url: "https://huggingface.co/aadi2026/finverify-lora" },
            { label: "GitHub", url: "#" },
            { label: "Paper PDF", url: "#" },
          ].map((l) => (
            <a key={l.label} href={l.url} target="_blank" rel="noreferrer"
              className="text-[10px] font-mono text-t-blue hover:text-t-cyan transition-colors">
              {l.label} &#8599;
            </a>
          ))}
        </div>
      </div>

      {/* ══ STAT CARDS ══ */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {STATS.map((s, i) => <StatCard key={i} {...s} />)}
      </div>

      {/* ══ ABLATION ══ */}
      <AblationSection />

      {/* ══ ERROR TAXONOMY ══ */}
      <ErrorTaxonomy />

      {/* ══ ROBUSTNESS ══ */}
      <div className="panel">
        <div className="panel-header">
          <span className="label">ROBUSTNESS ANALYSIS</span>
          <span className="text-[10px] text-t-muted font-mono">DVL under simulated real-world noise</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-[11px] font-mono">
            <thead>
              <tr className="text-t-muted border-b border-t-border">
                <th className="text-left py-2 px-3 font-normal">Condition</th>
                <th className="text-right py-2 px-3 font-normal">FT Only</th>
                <th className="text-right py-2 px-3 font-normal">FT+DVL</th>
                <th className="text-right py-2 px-3 font-normal">FT Drop</th>
                <th className="text-right py-2 px-3 font-normal">DVL Benefit</th>
              </tr>
            </thead>
            <tbody>
              {ROBUST.map((r, i) => (
                <tr key={i} className={`border-b border-t-border/50 ${r.highlight ? "border-l-2 border-l-t-green bg-t-green/[0.02]" : i % 2 === 0 ? "bg-white/[0.01]" : ""}`}>
                  <td className="py-2 px-3 text-t-primary">{r.cond}</td>
                  <td className="py-2 px-3 text-right text-t-secondary">{r.ft}</td>
                  <td className="py-2 px-3 text-right text-t-green">{r.dvl}</td>
                  <td className={`py-2 px-3 text-right ${r.drop === "—" ? "text-t-muted" : "text-t-red"}`}>{r.drop}</td>
                  <td className="py-2 px-3 text-right text-t-green font-semibold">{r.benefit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ══ HOW IT WORKS ══ */}
      <div>
        <div className="panel-header px-0 border-0 mb-3">
          <span className="label text-t-cyan text-[12px]">HOW IT WORKS</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Scale */}
          <div className="panel p-4 space-y-3">
            <div className="text-[11px] font-mono font-bold text-t-amber uppercase tracking-wider">Scale Correction</div>
            <div className="p-3 rounded bg-t-bg border border-t-border font-mono text-[12px] text-center">
              <span className="text-t-red">0.1240</span>
              <span className="text-t-muted mx-2">&rarr; &times;100 &rarr;</span>
              <span className="text-t-green">12.40%</span>
            </div>
            <p className="text-[10px] text-t-muted font-mono leading-relaxed">
              When financial ratios are expressed as decimals (0.12) but the question asks for a percentage, or vice versa. Triggered by keywords: margin, return, yield, growth, change, ratio.
            </p>
            <div className="text-[9px] text-t-muted font-mono border-t border-t-border pt-2">
              Paper case: CET1 ratio &mdash; predicted 10.935 &rarr; corrected to 0.10935
            </div>
          </div>

          {/* Sign */}
          <div className="panel p-4 space-y-3">
            <div className="text-[11px] font-mono font-bold text-t-purple uppercase tracking-wider">Sign Correction</div>
            <div className="p-3 rounded bg-t-bg border border-t-border font-mono text-[12px] text-center">
              <span className="text-t-red">-0.3411</span>
              <span className="text-t-muted mx-2">&rarr; |negate| &rarr;</span>
              <span className="text-t-green">+0.3411</span>
            </div>
            <p className="text-[10px] text-t-muted font-mono leading-relaxed">
              When the model computes the correct magnitude but inverts the sign. Common with directional questions. Applied only when magnitude matches within 5% tolerance.
            </p>
            <div className="text-[9px] text-t-muted font-mono border-t border-t-border pt-2">
              Paper case: HTM securities decrease &mdash; sign flipped from negative to positive
            </div>
          </div>

          {/* Magnitude */}
          <div className="panel p-4 space-y-3">
            <div className="text-[11px] font-mono font-bold text-t-green uppercase tracking-wider">Magnitude Correction</div>
            <div className="p-3 rounded bg-t-bg border border-t-border font-mono text-[12px] text-center">
              <span className="text-t-red">104.0</span>
              <span className="text-t-muted mx-2">&rarr; &times;10 &rarr;</span>
              <span className="text-t-green">1040.0</span>
              <span className="text-t-muted ml-1">&asymp; 995</span>
            </div>
            <p className="text-[10px] text-t-muted font-mono leading-relaxed">
              When figures appear in wrong unit denominations. Tries multipliers [&times;10, &times;100, &times;1000, &times;0.1, &times;0.01, &times;0.001] and applies the first match within 5% tolerance.
            </p>
            <div className="text-[9px] text-t-muted font-mono border-t border-t-border pt-2">
              Paper case: Class A shares &mdash; magnitude adjusted by &times;10
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
