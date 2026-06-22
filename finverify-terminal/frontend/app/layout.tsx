import type { Metadata, Viewport } from "next";
import "./globals.css";
import NavModeToggle from "@/components/NavModeToggle";
import NavHealthIndicator from "@/components/NavHealthIndicator";
import TickerBar from "@/components/TickerBar";
import { ConnectionProvider } from "@/lib/connection";

export const viewport: Viewport = {
  themeColor: "#0a0a0a",
};

export const metadata: Metadata = {
  title: "FinVerify Terminal",
  description:
    "Verification-first financial AI. 42× accuracy improvement on FinQA benchmark through deterministic correction of LLM numerical outputs.",
  openGraph: {
    title: "FinVerify Terminal — Financial LLM Verification",
    description:
      "Reduces numerical hallucination in financial LLMs through deterministic correction. 42× accuracy improvement on FinQA (n=873).",
    url: "https://finverify-llm.vercel.app",
    type: "website",
    images: [{ url: "/og", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "FinVerify Terminal",
    description:
      "42× accuracy improvement on FinQA through deterministic verification. Bloomberg-style financial AI terminal.",
    images: ["/og"],
  },
  metadataBase: new URL("https://finverify-llm.vercel.app"),
};

// Check if Clerk is configured at build/server time
const isClerkConfigured = !!(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

// Conditionally load Clerk components
async function getClerkComponents() {
  if (!isClerkConfigured) return null;
  try {
    const clerk = await import("@clerk/nextjs");
    const themes = await import("@clerk/themes");
    return { ...clerk, dark: themes.dark };
  } catch {
    return null;
  }
}

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const clerk = await getClerkComponents();

  const innerContent = (
    <html lang="en">
      <body className="antialiased min-h-screen flex flex-col">
        <ConnectionProvider>
          {/* ── Top Navbar ── */}
          <header className="flex items-center justify-between px-5 py-2 border-b border-t-border bg-t-bg sticky top-0 z-50">
            <div className="flex items-center gap-3">
              <a href="/" className="text-t-green font-bold text-sm tracking-widest font-mono">
                FINVERIFY TERMINAL
              </a>
              <span className="text-t-muted text-[10px] font-mono">v1.2</span>
              <NavModeToggle />
            </div>
            <div className="flex items-center gap-5">
              <NavHealthIndicator />

              {/* Auth section — only rendered when Clerk is configured */}
              {clerk && (
                <div className="flex items-center gap-2">
                  <clerk.SignedIn>
                    <a
                      href="/dashboard"
                      className="text-[10px] text-t-cyan font-mono font-semibold tracking-wider hover:text-t-cyan/80 transition-colors"
                    >
                      DASHBOARD
                    </a>
                    <clerk.UserButton
                      appearance={{
                        baseTheme: clerk.dark,
                        elements: { avatarBox: "w-[22px] h-[22px]" },
                      }}
                    />
                  </clerk.SignedIn>
                  <clerk.SignedOut>
                    <clerk.SignInButton mode="modal">
                      <button className="text-[10px] text-t-muted font-mono font-semibold tracking-wider hover:text-t-secondary transition-colors border border-t-border/50 px-2 py-0.5 rounded">
                        SIGN IN
                      </button>
                    </clerk.SignInButton>
                  </clerk.SignedOut>
                </div>
              )}

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
        </ConnectionProvider>
      </body>
    </html>
  );

  // Wrap with ClerkProvider only if configured
  if (clerk) {
    return (
      <clerk.ClerkProvider
        appearance={{
          baseTheme: clerk.dark,
          variables: {
            colorPrimary: "#00ff88",
            colorBackground: "#0a0a0a",
            colorText: "#e0e0e0",
          },
        }}
      >
        {innerContent}
      </clerk.ClerkProvider>
    );
  }

  return innerContent;
}
