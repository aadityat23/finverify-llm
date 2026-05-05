"use client";
import React, { useEffect, useState } from "react";
import type { QueryResponse } from "@/lib/api";

interface Props {
  result: QueryResponse | null;
}

function getTrustStyle(score: string) {
  if (score === "HIGH") return { text: "text-t-green", bg: "trust-high", glow: "glow-green", color: "#00ff88" };
  if (score === "MEDIUM") return { text: "text-t-amber", bg: "trust-medium", glow: "glow-amber", color: "#fbbf24" };
  return { text: "text-t-red", bg: "trust-low", glow: "glow-red", color: "#f87171" };
}

export default function TrustScore({ result }: Props) {
  const [displayNum, setDisplayNum] = useState<number | null>(null);

  // Counter animation
  useEffect(() => {
    if (!result?.verified_number) { setDisplayNum(null); return; }
    const target = result.verified_number;
    const duration = 600;
    const start = performance.now();
    const animate = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayNum(target * eased);
      if (progress < 1) requestAnimationFrame(animate);
      else setDisplayNum(target);
    };
    requestAnimationFrame(animate);
  }, [result?.verified_number]);

  if (!result) {
    return (
      <div className="panel">
        <div className="panel-header">
          <span className="label">VERIFIED OUTPUT</span>
        </div>
        <div className="p-3 text-center text-t-muted text-[10px] font-mono">
          Execute a query to see verified output
        </div>
      </div>
    );
  }

  const s = getTrustStyle(result.trust_score);
  const hasCorrections = result.correction_log.length > 0;

  return (
    <div className={`panel ${s.glow}`}>
      <div className="panel-header">
        <span className="label">VERIFIED OUTPUT</span>
        <div className={`trust-badge ${s.bg}`}>{result.trust_score}</div>
      </div>

      <div className="px-3 py-2.5">
        {/* Main display row */}
        <div className="flex items-start gap-4">
          {/* Verified number */}
          <div className="flex-1">
            <div
              className={`font-mono font-bold count-animate ${s.text}`}
              style={{ fontSize: "32px", lineHeight: 1.1, textShadow: `0 0 20px ${s.color}33` }}
            >
              {displayNum !== null ? result.display_value : "---"}
            </div>
            <div className="text-[9px] text-t-muted font-mono mt-1 uppercase tracking-wider">
              Verified Output
            </div>
          </div>

          {/* Trust info */}
          <div className="text-right space-y-1 shrink-0">
            <div className="text-[10px] text-t-secondary font-mono">
              {hasCorrections
                ? `${result.correction_log.length} CORRECTION${result.correction_log.length > 1 ? "S" : ""}`
                : "NO CORRECTIONS"}
            </div>
            {hasCorrections && (
              <div className="text-[9px] text-t-muted font-mono">
                {result.correction_log.map((c) => c.rule).join(" → ")}
              </div>
            )}
          </div>
        </div>

        {/* Pipeline visualization */}
        {hasCorrections && (
          <div className="mt-3 pt-2.5 border-t border-t-border">
            <div className="flex items-center gap-0 text-[10px] font-mono overflow-x-auto">
              {/* Start: raw number */}
              <div className="shrink-0 px-2 py-1 bg-[#1a0505] border border-t-red/30 rounded text-t-red">
                RAW: {result.raw_number}
              </div>
              {/* Each correction step */}
              {result.correction_log.map((c, i) => (
                <React.Fragment key={i}>
                  <div className="shrink-0 px-1.5 text-t-muted">
                    ——<span className="text-[8px] text-t-amber">[{c.rule}]</span>——▸
                  </div>
                  {i === result.correction_log.length - 1 && (
                    <div className="shrink-0 px-2 py-1 bg-[#051a0d] border border-t-green/30 rounded text-t-green">
                      VERIFIED: {c.after}
                    </div>
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
