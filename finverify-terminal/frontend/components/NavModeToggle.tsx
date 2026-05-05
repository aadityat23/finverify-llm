"use client";

import React from "react";
import { usePathname } from "next/navigation";

export default function NavModeToggle() {
  const pathname = usePathname();
  const isMarket = pathname === "/market";

  return (
    <div className="flex items-center border border-t-border rounded overflow-hidden">
      <a
        href="/"
        className={`px-3 py-1 text-[10px] font-mono font-bold uppercase tracking-wider transition-colors ${
          !isMarket
            ? "bg-t-green/10 text-t-green border-r border-t-border"
            : "text-t-muted hover:text-t-secondary border-r border-t-border"
        }`}
      >
        TERMINAL
      </a>
      <a
        href="/market"
        className={`px-3 py-1 text-[10px] font-mono font-bold uppercase tracking-wider transition-colors ${
          isMarket
            ? "bg-t-amber/10 text-t-amber"
            : "text-t-muted hover:text-t-secondary"
        }`}
      >
        MARKET
      </a>
    </div>
  );
}
