"use client";
import React, { useState, useEffect } from "react";
import type { CorrectionEntry } from "@/lib/api";

const RULE_DESC: Record<string, string> = {
  scale_mul100: "Decimal → percentage",
  scale_div100: "Percentage → decimal",
  sign_corrected: "Sign inverted",
};
function magDesc(rule: string) {
  const m = rule.match(/magnitude_x(.+)/);
  return m ? `Scale factor ×${m[1]}` : rule;
}

interface LogEntry {
  ts: string;
  event: string;
  detail: string;
  color: string;
  sub?: { label: string; value: string; color?: string }[];
}

interface Props {
  correctionLog: CorrectionEntry[];
  rawNumber: number | null;
  question: string;
  isLoading: boolean;
}

export default function VerificationLog({ correctionLog, rawNumber, question, isLoading }: Props) {
  const [visibleCount, setVisibleCount] = useState(0);

  // Build log entries
  const entries: LogEntry[] = [];
  if (rawNumber !== null) {
    let ms = 1;
    entries.push({
      ts: `00:00:${String(ms++).padStart(3, "0")}`,
      event: "INPUT",
      detail: String(rawNumber),
      color: "text-t-secondary",
    });

    // Detect keywords
    const ratioKW = ["ratio","percentage","percent","rate","margin","return","yield","growth","change","increase","decrease","loss"];
    const found = ratioKW.find((kw) => question.toLowerCase().includes(kw));
    if (found) {
      entries.push({
        ts: `00:00:${String(ms++).padStart(3, "0")}`,
        event: "KEYWORD",
        detail: `"${found}" → RATIO`,
        color: "text-t-amber",
      });
    }

    // Corrections
    for (const c of correctionLog) {
      const desc = RULE_DESC[c.rule] || magDesc(c.rule);
      entries.push({
        ts: `00:00:${String(ms++).padStart(3, "0")}`,
        event: "RULE",
        detail: c.rule,
        color: "text-t-green",
        sub: [
          { label: "IN", value: String(c.before) },
          { label: "OUT", value: String(c.after), color: "text-t-green" },
          { label: "WHY", value: desc },
        ],
      });
    }

    entries.push({
      ts: `00:00:${String(ms).padStart(3, "0")}`,
      event: correctionLog.length > 0 ? "DONE" : "CLEAN",
      detail: correctionLog.length > 0 ? "CORRECTED" : "VERIFIED",
      color: "text-t-green",
    });
  }

  // Stagger entries
  useEffect(() => {
    if (entries.length === 0) { setVisibleCount(0); return; }
    setVisibleCount(0);
    let i = 0;
    const iv = setInterval(() => {
      i++;
      setVisibleCount(i);
      if (i >= entries.length) clearInterval(iv);
    }, 120);
    return () => clearInterval(iv);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rawNumber, correctionLog.length]);

  return (
    <div className="panel flex flex-col">
      <div className="panel-header">
        <span className="label">DVL CORRECTION LOG</span>
        {isLoading && <span className="status-dot amber" />}
        {!isLoading && correctionLog.length > 0 && (
          <span className="text-[9px] text-t-amber font-mono">
            {correctionLog.length} CORRECTION{correctionLog.length > 1 ? "S" : ""}
          </span>
        )}
        {!isLoading && rawNumber !== null && correctionLog.length === 0 && (
          <span className="text-[9px] text-t-green font-mono">CLEAN</span>
        )}
      </div>

      <div className="px-2.5 py-1.5 relative scanline overflow-y-auto max-h-[240px] min-h-[70px]">
        {rawNumber === null && !isLoading && (
          <div className="text-t-muted text-[10px] font-mono py-3 text-center">
            Awaiting input...
          </div>
        )}

        {isLoading && (
          <div className="flex items-center gap-2 text-[10px] font-mono text-t-amber py-3">
            <span className="animate-blink">_</span> Running DVL pipeline...
          </div>
        )}

        {entries.slice(0, visibleCount).map((e, i) => (
          <div key={i} className="animate-fade-in mb-0.5">
            <div className="flex gap-2 text-[10px] font-mono leading-snug">
              <span className="text-t-muted shrink-0">[{e.ts}]</span>
              <span className={`${e.color} shrink-0 w-[60px]`}>{e.event}</span>
              <span className="text-t-primary">{e.detail}</span>
            </div>
            {e.sub?.map((s, j) => (
              <div key={j} className="flex gap-2 text-[10px] font-mono leading-snug pl-[88px]">
                <span className="text-t-muted w-[30px] text-right">{s.label}:</span>
                <span className={s.color || "text-t-secondary"}>{s.value}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
