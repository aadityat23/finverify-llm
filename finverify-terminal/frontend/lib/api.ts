/**
 * FinVerify Terminal — API Client
 * ================================
 * Typed fetch wrappers for the FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || API_BASE.replace(/^http/, "ws");

/* ─── Types ─── */

export interface CorrectionEntry {
  rule: string;
  before: number;
  after: number;
  description: string;
}

export interface QueryResponse {
  question: string;
  raw_text: string | null;
  raw_number: number | null;
  verified_number: number | null;
  correction_log: CorrectionEntry[];
  trust_score: string;
  trust_color: string;
  display_value: string;
  mode?: string;
  verified?: boolean;
}

export interface SampleQuery {
  question: string;
  actual: number | null;
  category: string | null;
}

export interface HealthStatus {
  status: string;
  model: string;
}

export interface MarketQuote {
  symbol: string;
  price: number;
  prev_close: number;
  change: number;
  change_pct: number;
  volume: number;
  market_cap: number;
  stale?: boolean;
  display_name?: string;
}

export interface MetricResult {
  symbol: string;
  metric: string;
  label: string;
  raw_value: number | null;
  question_text: string;
  verified_value: number | null;
  correction_log: CorrectionEntry[];
  trust_score: string;
  trust_color: string;
  stale?: boolean;
}

/* ─── DVL API Calls ─── */

export async function queryLLM(
  question: string,
  context?: string
): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, context }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Query failed (${res.status}): ${err}`);
  }
  return res.json();
}

export async function verifyNumber(
  question: string,
  rawNumber: number
): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, raw_number: rawNumber }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Verify failed (${res.status}): ${err}`);
  }
  return res.json();
}

export async function checkHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("Backend unreachable");
  return res.json();
}

export async function getSampleQueries(): Promise<SampleQuery[]> {
  const res = await fetch(`${API_BASE}/sample-queries`);
  if (!res.ok) throw new Error("Failed to fetch sample queries");
  return res.json();
}

/* ─── Market API Calls ─── */

export async function getMarketQuotes(symbols?: string[]): Promise<MarketQuote[]> {
  const params = symbols ? `?symbols=${symbols.join(",")}` : "";
  const res = await fetch(`${API_BASE}/market/quotes${params}`);
  if (!res.ok) throw new Error("Failed to fetch quotes");
  return res.json();
}

export async function getMarketIndices(): Promise<MarketQuote[]> {
  const res = await fetch(`${API_BASE}/market/indices`);
  if (!res.ok) throw new Error("Failed to fetch indices");
  return res.json();
}

export async function getVerifiedMetric(symbol: string, metric: string): Promise<MetricResult> {
  const res = await fetch(`${API_BASE}/market/verified-metrics?symbol=${symbol}&metric=${metric}`);
  if (!res.ok) throw new Error("Failed to fetch metric");
  return res.json();
}

export async function getAllMetrics(symbol: string): Promise<MetricResult[]> {
  const res = await fetch(`${API_BASE}/market/all-metrics?symbol=${symbol}`);
  if (!res.ok) throw new Error("Failed to fetch metrics");
  return res.json();
}

/* ─── WebSocket ─── */

export function createMarketWebSocket(
  onMessage: (quotes: MarketQuote[]) => void,
  onError?: (err: Event) => void,
): WebSocket | null {
  try {
    const ws = new WebSocket(`${WS_BASE}/ws/market`);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (Array.isArray(data)) {
          onMessage(data);
        }
      } catch { /* ignore parse errors */ }
    };
    ws.onerror = (e) => onError?.(e);
    return ws;
  } catch {
    return null;
  }
}
