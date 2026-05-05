"use client";
import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";

const ERRORS = [
  { name: "Reasoning close (<50% rel.)", count: 210, pct: 39.0, color: "#ef4444" },
  { name: "Reasoning far (>50% rel.)", count: 184, pct: 34.1, color: "#f87171" },
  { name: "Magnitude (>2 orders)", count: 66, pct: 12.2, color: "#fbbf24" },
  { name: "Order-of-magnitude (1-2 ord.)", count: 62, pct: 11.4, color: "#60a5fa" },
  { name: "Sign error", count: 9, pct: 1.6, color: "#00ff88" },
  { name: "Scale error", count: 4, pct: 0.8, color: "#22d3ee" },
  { name: "Unknown", count: 4, pct: 0.8, color: "#444" },
];

interface TipProps { active?: boolean; payload?: Array<{ payload: typeof ERRORS[0] }> }
function PieTip({ active, payload }: TipProps) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="panel px-3 py-2 text-[11px] font-mono border border-t-border-accent">
      <div className="text-t-primary">{d.name}</div>
      <div style={{ color: d.color }}>{d.count} cases ({d.pct}%)</div>
    </div>
  );
}

export default function ErrorTaxonomy() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* LEFT — Donut chart */}
      <div className="panel">
        <div className="panel-header">
          <span className="label">ERROR TAXONOMY</span>
          <span className="text-[10px] text-t-muted font-mono">n=539 errors analyzed</span>
        </div>
        <div className="p-4 h-[300px] relative">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={ERRORS} cx="50%" cy="50%" innerRadius={65} outerRadius={110} dataKey="count" paddingAngle={1} animationDuration={1200}>
                {ERRORS.map((e, i) => <Cell key={i} fill={e.color} fillOpacity={0.85} stroke="#0a0a0a" strokeWidth={2} />)}
              </Pie>
              <Tooltip content={<PieTip />} />
            </PieChart>
          </ResponsiveContainer>
          {/* Center label */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="text-center">
              <div className="text-2xl font-bold font-mono text-t-primary">539</div>
              <div className="text-[9px] text-t-muted font-mono uppercase">total errors</div>
            </div>
          </div>
        </div>
      </div>

      {/* RIGHT — Breakdown */}
      <div className="panel">
        <div className="panel-header">
          <span className="label">ERROR BREAKDOWN</span>
        </div>
        <div className="p-4 space-y-3">
          {/* Key insight */}
          <div className="p-3 rounded border border-t-red/20 bg-t-red/[0.04]">
            <div className="text-[10px] text-t-red font-mono font-semibold uppercase tracking-wider mb-1">Key Insight</div>
            <p className="text-[11px] text-t-secondary font-mono leading-relaxed">
              73.1% of failures are multi-step reasoning errors — where the model locates the correct figures but loses numerical precision across sequential computation steps.
            </p>
          </div>

          {/* Error list */}
          <div className="space-y-1.5">
            {ERRORS.map((e, i) => (
              <div key={i} className="flex items-center gap-2 text-[11px] font-mono">
                <span className="w-2 h-2 rounded-sm shrink-0" style={{ background: e.color }} />
                <span className="flex-1 text-t-secondary truncate">{e.name}</span>
                <span className="text-t-muted shrink-0">{e.count}</span>
                <span className="w-12 text-right shrink-0" style={{ color: e.color }}>{e.pct}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
