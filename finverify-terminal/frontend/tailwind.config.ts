import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        "t-bg": "#0a0a0a",
        "t-surface": "#111111",
        "t-border": "#1e1e1e",
        "t-border-accent": "#2a2a2a",
        "t-primary": "#e0e0e0",
        "t-secondary": "#888888",
        "t-muted": "#444444",
        "t-green": "#00ff88",
        "t-amber": "#fbbf24",
        "t-red": "#f87171",
        "t-blue": "#60a5fa",
        "t-cyan": "#22d3ee",
        "t-purple": "#a78bfa",
      },
      fontFamily: {
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "Cascadia Code",
          "Fira Code",
          "monospace",
        ],
      },
      animation: {
        "blink": "blink 1s step-end infinite",
        "fade-in": "fadeIn 0.3s ease-out",
        "slide-up": "slideUp 0.4s ease-out",
        "glow-pulse": "glowPulse 2s ease-in-out infinite",
      },
      keyframes: {
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
        fadeIn: {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        glowPulse: {
          "0%, 100%": { boxShadow: "0 0 4px rgba(0,255,136,0.2)" },
          "50%": { boxShadow: "0 0 16px rgba(0,255,136,0.4)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
