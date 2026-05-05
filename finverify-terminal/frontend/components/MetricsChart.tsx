"use client";
import React from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";

const ABLATION = [
  { name: "Baseline", accuracy: 1.0, color: "#f87171" },
  { name: "+ Context", accuracy: 24.0, color: "#fb923c" },
  { name: "+ DVL v1", accuracy: 32.0, color: "#fbbf24" },
  { name: "+ QLoRA", accuracy: 38.5, color: "#a78bfa" },
  { name: "+ DVL v2", accuracy: 42.61, color: "#00ff88" },
];

const ERRORS = [
  { name: "Reasoning", value: 45.2, color: "#f87171" },
  { name: "Magnitude", value: 18.3, color: "#fbbf24" },
  { name: "Scale", value: 14.1, color: "#fb923c" },
  { name: "Sign", value: 8.7, color: "#a78bfa" },
  { name: "Extraction", value: 7.4, color: "#22d3ee" },
  { name: "Other", value: 6.3, color: "#444" },
];

interface TipProps { active?: boolean; payload?: Array<{ value: number; payload: { name: string } }> }
function Tip({ active, payload }: TipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="panel px-3 py-2 text-[11px] font-mono">
      <div className="text-t-primary">{payload[0].payload.name}</div>
      <div className="text-t-green">{payload[0].value.toFixed(1)}%</div>
    </div>
  );
}

export default function MetricsChart() {
  return (
    <div className="space-y-4">
      <div className="panel p-5">
        <div className="panel-header px-0 border-0 pb-3">
          <span className="label text-t-cyan">ABLATION STUDY</span>
          <span className="text-[10px] text-t-muted font-mono">Accuracy by pipeline stage</span>
        </div>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={ABLATION} margin={{ top: 5, right: 5, left: -15, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e1e1e" />
              <XAxis dataKey="name" tick={{ fill: "#444", fontSize: 10, fontFamily: "JetBrains Mono" }} axisLine={{ stroke: "#1e1e1e" }} />
              <YAxis tick={{ fill: "#444", fontSize: 10, fontFamily: "JetBrains Mono" }} axisLine={{ stroke: "#1e1e1e" }} domain={[0, 50]} tickFormatter={(v: number) => `${v}%`} />
              <Tooltip content={<Tip />} cursor={{ fill: "rgba(255,255,255,0.02)" }} />
              <Bar dataKey="accuracy" radius={[3, 3, 0, 0]}>
                {ABLATION.map((e, i) => <Cell key={i} fill={e.color} fillOpacity={0.85} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="panel p-5">
        <div className="panel-header px-0 border-0 pb-3">
          <span className="label text-t-cyan">ERROR TAXONOMY</span>
          <span className="text-[10px] text-t-muted font-mono">Distribution of failure modes</span>
        </div>
        <div className="space-y-2.5">
          {ERRORS.map((e) => (
            <div key={e.name} className="flex items-center gap-3">
              <div className="w-20 text-[11px] font-mono text-t-secondary">{e.name}</div>
              <div className="flex-1 h-3 rounded-sm overflow-hidden bg-t-bg">
                <div className="h-full rounded-sm transition-all duration-1000" style={{ width: `${e.value}%`, background: e.color, opacity: 0.75 }} />
              </div>
              <div className="w-10 text-[11px] font-mono text-t-muted text-right">{e.value}%</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
