/**
 * Client-side DVL (Deterministic Verification Layer)
 * ===================================================
 * Lightweight JS port of the backend DVL engine.
 * Used as fallback when backend API is unreachable.
 */

export interface DVLResult {
  verified: number;
  logs: string[];
  trust: "HIGH" | "MEDIUM" | "LOW";
  trustColor: string;
}

const RATIO_KEYWORDS = [
  "ratio", "margin", "return", "yield", "growth", "change",
  "increase", "decrease", "percent", "rate",
];

export function clientDVL(question: string, raw: number): DVLResult {
  const isRatio = RATIO_KEYWORDS.some((k) =>
    question.toLowerCase().includes(k),
  );
  let value = raw;
  const logs: string[] = [];

  // Scale correction — only for clear cases
  if (isRatio && Math.abs(value) > 100) {
    const corrected = value / 100;
    logs.push(`scale_div100: ${value} → ${corrected}`);
    value = corrected;
  } else if (isRatio && Math.abs(value) < 1) {
    const corrected = value * 100;
    logs.push(`scale_mul100: ${value} → ${corrected}`);
    value = corrected;
  }
  // 1–100 range: AMBIGUOUS — no correction applied

  // Trust scoring
  if (logs.length === 0) {
    return { verified: value, logs, trust: "HIGH", trustColor: "#00ff88" };
  }
  // Scale corrections (mul100, div100) are expected, deterministic corrections.
  // These demonstrate DVL value — they should always be MEDIUM trust.
  const isScaleCorrection = logs.some(
    (l) => l.startsWith("scale_mul100") || l.startsWith("scale_div100")
  );
  if (isScaleCorrection) {
    return { verified: value, logs, trust: "MEDIUM", trustColor: "#fbbf24" };
  }
  // Other corrections: use delta to determine trust
  const delta = Math.abs(value - raw) / (Math.abs(raw) + 1e-10);
  if (delta < 0.5) {
    return { verified: value, logs, trust: "MEDIUM", trustColor: "#fbbf24" };
  }
  return { verified: value, logs, trust: "LOW", trustColor: "#f87171" };
}
