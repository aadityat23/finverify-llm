"use client";
import React, { useState, useRef, useEffect } from "react";

const SAMPLES = [
  "YoY operating margin change?",
  "CET1 ratio Q4 2022?",
  "Net income increase YoY?",
  "Revenue growth rate?",
  "HTM securities decrease?",
  "Class A shares outstanding change?",
];

interface Props {
  onSubmit: (q: string) => void;
  onRunDemo: () => void;
  isLoading: boolean;
  demoStatus: string | null; // e.g. "DEMO 1/3..." or null
}

export default function QueryInput({ onSubmit, onRunDemo, isLoading, demoStatus }: Props) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { ref.current?.focus(); }, []);

  // Global keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Escape to clear
      if (e.key === "Escape") {
        setValue("");
        ref.current?.focus();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const submit = () => {
    if (!value.trim() || isLoading) return;
    onSubmit(value.trim());
    setValue("");
  };

  const isMac = typeof navigator !== "undefined" && /Mac/.test(navigator.userAgent);

  return (
    <div className="panel flex flex-col h-full">
      {/* Header */}
      <div className="panel-header">
        <span className="label">QUERY INPUT</span>
        <span className={`status-dot ${isLoading ? "amber" : ""}`} />
      </div>

      <div className="flex-1 flex flex-col p-2.5 gap-2 overflow-y-auto">
        {/* DVL Status Dashboard */}
        <div className="bg-[#0d0d0d] border border-t-border/60 rounded px-3 py-2">
          <div className="text-[9px] text-t-muted font-mono uppercase tracking-wider mb-1.5">DVL ENGINE STATUS</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px] font-mono">
            <div className="flex items-center gap-1.5">
              <span className="w-[5px] h-[5px] rounded-full bg-t-green inline-block" />
              <span className="text-t-secondary">ENGINE:</span>
              <span className="text-t-green">ONLINE</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-t-secondary">RULES:</span>
              <span className="text-t-primary">3</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-t-secondary">MODEL:</span>
              <span className="text-t-cyan">finverify-lora</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-t-secondary">TOLERANCE:</span>
              <span className="text-t-amber">5%</span>
            </div>
          </div>
        </div>

        {/* Textarea */}
        <div className="relative">
          <textarea
            ref={ref}
            id="query-input"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); submit(); }
              if (e.key === "Enter" && !e.shiftKey && !e.metaKey && !e.ctrlKey) { e.preventDefault(); submit(); }
            }}
            placeholder="Enter financial question..."
            disabled={isLoading}
            rows={3}
            className="w-full bg-transparent text-t-green text-[12px] font-mono resize-none outline-none placeholder:text-t-green/20 border border-t-border focus:border-t-green/30 transition-colors p-2 rounded"
          />
          <span className="absolute bottom-2 right-2 text-[9px] text-t-muted/50 font-mono">
            {isMac ? "⌘" : "Ctrl"}+↵ to execute
          </span>
        </div>

        {/* Execute button */}
        <button
          id="execute-btn"
          onClick={submit}
          disabled={isLoading || !value.trim()}
          className="w-full py-2 text-[11px] font-mono font-bold uppercase tracking-[0.15em] rounded transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
          style={{
            background: isLoading ? "rgba(251,191,36,0.06)" : "rgba(251,191,36,0.1)",
            color: "#fbbf24",
            border: "1px solid rgba(251,191,36,0.2)",
            ...((!isLoading && value.trim()) ? { boxShadow: "0 0 8px rgba(251,191,36,0.15)" } : {}),
          }}
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              {demoStatus || "PROCESSING"}<span className="animate-pulse">...</span>
            </span>
          ) : "EXECUTE"}
        </button>

        {/* RUN DEMO button */}
        <button
          id="run-demo-btn"
          onClick={onRunDemo}
          disabled={isLoading}
          className="w-full py-2 text-[11px] font-mono font-bold uppercase tracking-[0.12em] rounded transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
          style={{
            background: "rgba(251,191,36,0.06)",
            color: "#fbbf24",
            border: "1px solid rgba(251,191,36,0.15)",
          }}
        >
          {demoStatus ? demoStatus : "▶ RUN DEMO"}
        </button>

        {/* Sample queries */}
        <div>
          <div className="text-[9px] text-t-muted font-mono uppercase tracking-wider mb-1.5">
            Sample Queries
          </div>
          <div className="flex flex-wrap gap-1">
            {SAMPLES.map((q, i) => (
              <button
                key={i}
                id={`sample-${i}`}
                onClick={() => { setValue(q); ref.current?.focus(); }}
                className="text-[9px] font-mono px-2 py-0.5 rounded border border-t-border text-t-secondary hover:text-t-cyan hover:border-t-cyan/30 transition-all duration-200"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* System Constraints */}
        <div className="bg-[#0d0d0d] border border-t-border/60 rounded px-3 py-2 mt-auto">
          <div className="text-[9px] text-t-muted font-mono uppercase tracking-wider mb-1.5">SYSTEM CONSTRAINTS</div>
          <div className="space-y-0.5 text-[10px] font-mono">
            <div className="flex items-center gap-2">
              <span className="text-t-green">✓</span>
              <span className="text-t-secondary">Numerical queries: verified with DVL</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-t-red">✗</span>
              <span className="text-t-secondary">Advisory queries: returned unverified</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-t-red">✗</span>
              <span className="text-t-secondary">Open-ended: LLM response only</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
