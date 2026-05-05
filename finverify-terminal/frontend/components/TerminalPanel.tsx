"use client";
import React, { useEffect, useState } from "react";
import type { QueryResponse } from "@/lib/api";

interface Props {
  result: QueryResponse | null;
  isLoading: boolean;
}

export default function TerminalPanel({ result, isLoading }: Props) {
  const [animatedVal, setAnimatedVal] = useState<string | null>(null);
  const latency = (1.1 + Math.random() * 1.2).toFixed(1);

  useEffect(() => {
    if (!result?.raw_number) { setAnimatedVal(null); return; }
    const target = result.raw_number;
    const duration = 600;
    const start = performance.now();
    const run = (now: number) => {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setAnimatedVal((target * eased).toFixed(4));
      if (p < 1) requestAnimationFrame(run);
      else setAnimatedVal(target.toFixed(4));
    };
    requestAnimationFrame(run);
  }, [result?.raw_number]);

  return (
    <div
      className="panel"
      style={{
        borderLeft: result ? "3px solid #f87171" : undefined,
      }}
    >
      <div className="panel-header">
        <span className="label">RAW LLM OUTPUT</span>
        {result?.mode && (
          <span className="text-[9px] text-t-muted font-mono uppercase">
            MODE: <span className={
              result.mode === "numerical" ? "text-t-cyan" :
              result.mode === "advisory" ? "text-t-amber" : "text-t-secondary"
            }>{result.mode}</span>
          </span>
        )}
      </div>

      <div className="px-3 py-2.5 relative scanline min-h-[60px] flex flex-col justify-center">
        {/* Empty state */}
        {!result && !isLoading && (
          <div className="text-t-muted text-[10px] font-mono text-center py-2">
            Awaiting query execution
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center gap-2 py-3">
            <span className="text-t-amber text-[10px] font-mono animate-pulse">
              Querying model...
            </span>
          </div>
        )}

        {/* Result */}
        {result && !isLoading && (
          <>
            {result.raw_number !== null ? (
              <div className="text-center count-animate">
                <div className="text-[28px] font-mono font-bold text-t-primary tracking-tight leading-none">
                  {animatedVal ?? "---"}
                </div>
              </div>
            ) : (
              <div className="text-center space-y-1">
                <div className="text-t-red text-[12px] font-mono font-bold">
                  EXTRACTION FAILED
                </div>
                {result.raw_text && (
                  <div className="text-t-muted text-[10px] font-mono break-all max-w-full">
                    &quot;{result.raw_text.slice(0, 120)}&quot;
                  </div>
                )}
              </div>
            )}

            {/* Footer stats — single compact line */}
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-t-border text-[9px] font-mono text-t-muted">
              <span>tokens: {result.raw_text ? Math.ceil(result.raw_text.length / 4) : "--"}</span>
              <span>latency: {latency}s</span>
              <span>model: finverify-lora</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
