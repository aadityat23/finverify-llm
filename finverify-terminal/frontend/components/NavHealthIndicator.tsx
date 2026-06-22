"use client";

import React from "react";
import { useConnection } from "@/lib/connection";

/**
 * NavHealthIndicator — Reactive health indicator in the top navbar.
 * Shows connection status based on actual /health checks, not hardcoded.
 * ● LIVE (green)     — backend healthy
 * ● DEGRADED (amber) — backend unreachable, using client-side DVL
 * ● ... (gray)       — still checking
 */
export default function NavHealthIndicator() {
  const { status, modelName } = useConnection();

  const dotColor =
    status === "online"
      ? "bg-t-green animate-glow-pulse"
      : status === "degraded"
        ? "bg-t-amber animate-pulse"
        : "bg-t-muted animate-pulse";

  const labelColor =
    status === "online"
      ? "text-t-green"
      : status === "degraded"
        ? "text-t-amber"
        : "text-t-muted";

  const labelText =
    status === "online"
      ? "LIVE"
      : status === "degraded"
        ? "DEGRADED"
        : "...";

  return (
    <span className="hidden sm:flex items-center gap-2 text-[11px] text-t-secondary font-mono">
      MODEL: {modelName}
      <span className={`w-[6px] h-[6px] rounded-full inline-block ${dotColor}`} />
      <span className={`text-[10px] font-bold ${labelColor}`}>
        ● {labelText}
      </span>
      {status === "degraded" && (
        <span className="text-[8px] text-t-amber font-mono" title="Backend unreachable — using client-side DVL">
          — using demo mode
        </span>
      )}
    </span>
  );
}
