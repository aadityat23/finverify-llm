import type { Metadata, Viewport } from "next";
import "./globals.css";
import NavModeToggle from "@/components/NavModeToggle";
import TickerBar from "@/components/TickerBar";

export const viewport: Viewport = {
  themeColor: "#0a0a0a",
};

export const metadata: Metadata = {
  title: "FinVerify Terminal",
  description:
    "Bloomberg-dark financial LLM verification terminal with Deterministic Verification Layer. 42x accuracy on FinQA (n=873).",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen flex flex-col">
        {/* ── Top Navbar ── */}
        <header className="flex items-center justify-between px-5 py-2 border-b border-t-border bg-t-bg sticky top-0 z-50">
          <div className="flex items-center gap-3">
            <a href="/" className="text-t-green font-bold text-sm tracking-widest font-mono">
              FINVERIFY TERMINAL
            </a>
            <span className="text-t-muted text-[10px] font-mono">v1.1</span>
            <NavModeToggle />
          </div>
          <div className="flex items-center gap-5">
            <span className="hidden sm:flex items-center gap-2 text-[11px] text-t-secondary font-mono">
              MODEL: aadi2026/finverify-lora
              <span className="w-[6px] h-[6px] rounded-full bg-t-green inline-block animate-glow-pulse" />
              <span className="text-t-green text-[10px] font-bold">LIVE</span>
            </span>
            <a
              href="/metrics"
              className="text-[11px] text-t-amber font-mono font-semibold tracking-wider hover:text-t-amber/80 transition-colors"
            >
              RESEARCH
            </a>
          </div>
        </header>

        {/* ── Live Market Ticker Strip ── */}
        <TickerBar />

        {/* ── Page content ── */}
        <main className="flex-1">{children}</main>
      </body>
    </html>
  );
}
