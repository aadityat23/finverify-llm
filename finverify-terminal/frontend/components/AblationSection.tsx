"use client";
import React from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";

const ABLATION = [
  { name: "Baseline", accuracy: 1.0, ci: "[0.4, 1.9]", delta: null, color: "#f87171" },
  { name: "+Doc Context", accuracy: 24.0, ci: "[21.2, 26.9]", delta: "+23.0pp", color: "#fb923c" },
  { name: "+DVL v1", accuracy: 32.0, ci: "[29.0, 35.1]", delta: "+8.0pp", color: "#fbbf24" },
  { name: "+QLoRA FT", accuracy: 38.5, ci: "[35.4, 41.7]", delta: "+6.5pp", color: "#a78bfa" },
  { name: "+DVL v2", accuracy: 42.61, ci: "[39.5, 45.7]", delta: "+4.1pp", color: "#00ff88" },
];

const NEGATIVE = [
  { name: "+CoT zero-shot", accuracy: 29.5, ci: "[26.6, 32.6]", delta: "-9.0pp" },
  { name: "+CoT FT v1 (3K)", accuracy: 26.5, ci: "[23.7, 29.5]", delta: "-12.0pp" },
  { name: "+Cross-doc RAG", accuracy: 31.0, ci: "[28.0, 34.1]", delta: "-7.5pp" },
];

interface TipProps { active?: boolean; payload?: Array<{ value: number; payload: { name: string; ci: string } }> }
function ChartTip({ active, payload }: TipProps) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="panel px-3 py-2 text-[11px] font-mono border border-t-border-accent">
      <div className="text-t-primary font-semibold">{d.payload.name}</div>
      <div className="text-t-green">{d.value.toFixed(2)}%</div>
      <div className="text-t-muted">95% CI: {d.payload.ci}</div>
    </div>
  );
}

export default function AblationSection() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* LEFT — Tables */}
      <div className="space-y-4">
        {/* Main ablation */}
        <div className="panel">
          <div className="panel-header">
            <span className="label">ABLATION STUDY</span>
            <span className="text-[10px] text-t-muted font-mono">Progressive pipeline</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[11px] font-mono">
              <thead>
                <tr className="text-t-muted border-b border-t-border">
                  <th className="text-left py-2 px-3 font-normal">Configuration</th>
                  <th className="text-right py-2 px-3 font-normal">Accuracy</th>
                  <th className="text-right py-2 px-3 font-normal">95% CI</th>
                  <th className="text-right py-2 px-3 font-normal">Delta</th>
                </tr>
              </thead>
              <tbody>
                {ABLATION.map((r, i) => {
                  const isLast = i === ABLATION.length - 1;
                  return (
                    <tr key={i} className={`border-b border-t-border/50 ${i % 2 === 0 ? "bg-white/[0.01]" : ""} ${isLast ? "border-l-2 border-l-t-green" : ""}`}>
                      <td className={`py-2 px-3 ${isLast ? "text-t-green font-semibold" : "text-t-primary"}`}>{r.name}</td>
                      <td className={`py-2 px-3 text-right ${isLast ? "text-t-green font-bold" : "text-t-primary"}`}>{r.accuracy.toFixed(2)}%</td>
                      <td className="py-2 px-3 text-right text-t-muted">{r.ci}</td>
                      <td className={`py-2 px-3 text-right ${r.delta ? "text-t-green" : "text-t-muted"}`}>{r.delta ?? "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Negative results */}
        <div className="panel">
          <div className="panel-header">
            <span className="label text-t-red">NEGATIVE RESULTS</span>
            <span className="text-[10px] text-t-muted font-mono">Approaches that degraded accuracy</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[11px] font-mono">
              <thead>
                <tr className="text-t-muted border-b border-t-border">
                  <th className="text-left py-2 px-3 font-normal">Configuration</th>
                  <th className="text-right py-2 px-3 font-normal">Accuracy</th>
                  <th className="text-right py-2 px-3 font-normal">95% CI</th>
                  <th className="text-right py-2 px-3 font-normal">Delta</th>
                </tr>
              </thead>
              <tbody>
                {NEGATIVE.map((r, i) => (
                  <tr key={i} className={`border-b border-t-border/50 ${i % 2 === 0 ? "bg-white/[0.01]" : ""}`}>
                    <td className="py-2 px-3 text-t-secondary">{r.name}</td>
                    <td className="py-2 px-3 text-right text-t-secondary">{r.accuracy.toFixed(2)}%</td>
                    <td className="py-2 px-3 text-right text-t-muted">{r.ci}</td>
                    <td className="py-2 px-3 text-right text-t-red">{r.delta}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* RIGHT — Bar chart */}
      <div className="panel">
        <div className="panel-header">
          <span className="label">ACCURACY PROGRESSION</span>
        </div>
        <div className="p-4 h-[380px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={ABLATION} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e1e1e" horizontal={false} />
              <XAxis type="number" domain={[0, 50]} tick={{ fill: "#444", fontSize: 10, fontFamily: "JetBrains Mono" }} axisLine={{ stroke: "#1e1e1e" }} tickFormatter={(v: number) => `${v}%`} />
              <YAxis type="category" dataKey="name" tick={{ fill: "#888", fontSize: 10, fontFamily: "JetBrains Mono" }} axisLine={{ stroke: "#1e1e1e" }} width={90} />
              <Tooltip content={<ChartTip />} cursor={{ fill: "rgba(255,255,255,0.02)" }} />
              <Bar dataKey="accuracy" radius={[0, 3, 3, 0]} animationDuration={1500}>
                {ABLATION.map((e, i) => <Cell key={i} fill={e.color} fillOpacity={0.85} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
