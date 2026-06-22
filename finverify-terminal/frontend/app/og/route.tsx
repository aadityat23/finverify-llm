import { ImageResponse } from "next/og";

export const runtime = "edge";

export async function GET() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "1200px",
          height: "630px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          background: "#0a0a0a",
          fontFamily: "monospace",
          position: "relative",
        }}
      >
        {/* Subtle scanline overlay */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.05) 2px, rgba(0,0,0,0.05) 4px)",
          }}
        />

        {/* Border frame */}
        <div
          style={{
            position: "absolute",
            inset: "20px",
            border: "1px solid #1e1e1e",
            borderRadius: "8px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            padding: "60px",
          }}
        >
          {/* Title */}
          <div
            style={{
              fontSize: "48px",
              fontWeight: 700,
              color: "#00ff88",
              letterSpacing: "0.12em",
              marginBottom: "16px",
            }}
          >
            FINVERIFY TERMINAL
          </div>

          {/* Subtitle */}
          <div
            style={{
              fontSize: "22px",
              color: "#e0e0e0",
              marginBottom: "24px",
              textAlign: "center",
            }}
          >
            42× accuracy improvement on FinQA benchmark
          </div>

          {/* DVL label */}
          <div
            style={{
              fontSize: "16px",
              color: "#fbbf24",
              letterSpacing: "0.08em",
              marginBottom: "40px",
            }}
          >
            Deterministic Verification Layer
          </div>

          {/* Ablation mini-table */}
          <div
            style={{
              display: "flex",
              gap: "24px",
              alignItems: "flex-end",
            }}
          >
            {[
              { label: "Baseline", pct: "1.0%", h: 8, color: "#f87171" },
              { label: "+Context", pct: "24.0%", h: 50, color: "#fbbf24" },
              { label: "+DVL v1", pct: "32.0%", h: 70, color: "#fbbf24" },
              { label: "+QLoRA", pct: "38.5%", h: 85, color: "#38bdf8" },
              { label: "+DVL v2", pct: "42.6%", h: 100, color: "#00ff88" },
            ].map((item) => (
              <div
                key={item.label}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <div style={{ fontSize: "14px", color: item.color, fontWeight: 700 }}>
                  {item.pct}
                </div>
                <div
                  style={{
                    width: "80px",
                    height: `${item.h}px`,
                    background: item.color + "33",
                    border: `1px solid ${item.color}55`,
                    borderRadius: "4px 4px 0 0",
                  }}
                />
                <div style={{ fontSize: "11px", color: "#666" }}>{item.label}</div>
              </div>
            ))}
          </div>

          {/* Footer */}
          <div
            style={{
              position: "absolute",
              bottom: "24px",
              display: "flex",
              gap: "24px",
              fontSize: "13px",
              color: "#444",
            }}
          >
            <span>n=873 · FinQA Dev Set</span>
            <span>·</span>
            <span>Mistral-7B + QLoRA</span>
            <span>·</span>
            <span>finverify-llm.vercel.app</span>
          </div>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  );
}
