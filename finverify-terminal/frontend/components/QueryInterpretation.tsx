"use client";
import React from "react";
import type { QueryResponse } from "@/lib/api";

/**
 * QueryInterpretation — Shows what the system understood from the query.
 * Displays between query input and raw output panel.
 */

const RATIO_KW = ["ratio","percentage","percent","rate","margin","return","yield","growth","change","increase","decrease","loss"];

interface Props {
  result: QueryResponse | null;
}

export default function QueryInterpretation({ result }: Props) {
  if (!result) return null;

  const question = result.question.toLowerCase();
  const detectedKeywords = RATIO_KW.filter((kw) => question.includes(kw));
  const isNumerical = result.mode === "numerical";
  const rulesArmed: string[] = [];
  if (detectedKeywords.length > 0) {
    rulesArmed.push("scale_mul100", "scale_div100");
  }
  rulesArmed.push("sign_correction");

  return (
    <div className="panel bg-[#0d0d0d] border-t-border/60">
      <div className="px-3 py-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-[9px] font-mono">
        <div className="flex items-center gap-1.5">
          <span className="text-t-muted uppercase tracking-wider">QUERY TYPE:</span>
          <span className={isNumerical ? "text-t-cyan" : "text-t-amber"}>
            {(result.mode ?? "numerical").toUpperCase()}
          </span>
        </div>
        {detectedKeywords.length > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="text-t-muted uppercase tracking-wider">KEYWORDS:</span>
            {detectedKeywords.map((kw) => (
              <span key={kw} className="text-t-amber bg-t-amber/10 px-1 py-0.5 rounded border border-t-amber/20">
                &quot;{kw}&quot;
              </span>
            ))}
          </div>
        )}
        <div className="flex items-center gap-1.5">
          <span className="text-t-muted uppercase tracking-wider">DVL RULES ARMED:</span>
          {rulesArmed.map((rule) => (
            <span key={rule} className="text-t-green bg-t-green/8 px-1 py-0.5 rounded border border-t-green/15">
              {rule}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
