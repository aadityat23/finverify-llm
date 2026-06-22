/**
 * FinVerify Terminal — Live Market Data (Finnhub)
 * ================================================
 * Fetches real stock quotes and financial metrics from Finnhub free tier.
 * Free tier: 60 calls/minute, no CC required.
 * If NEXT_PUBLIC_FINNHUB_KEY is not set, all functions return null gracefully.
 */

const FINNHUB_KEY = process.env.NEXT_PUBLIC_FINNHUB_KEY ?? '';

/* ─── Types ─── */

export interface FinnhubQuote {
  symbol: string;
  price: number;
  change: number;
  changePct: number;
  prevClose: number;
}

export interface FinnhubFinancials {
  symbol: string;
  peRatio: number | null;
  profitMargin: number | null;
  roe: number | null;
  revenueGrowth: number | null;
}

/* ─── Quote API ─── */

export async function getQuote(symbol: string): Promise<FinnhubQuote | null> {
  if (!FINNHUB_KEY) return null;
  try {
    const res = await fetch(
      `https://finnhub.io/api/v1/quote?symbol=${symbol}&token=${FINNHUB_KEY}`
    );
    if (!res.ok) return null;
    const data = await res.json();
    // Finnhub returns: c (current), d (change), dp (% change), o (open), pc (prev close)
    // If price is 0, the symbol is likely invalid
    if (!data.c || data.c === 0) return null;
    return {
      symbol,
      price: data.c,
      change: data.d ?? 0,
      changePct: data.dp ?? 0,
      prevClose: data.pc ?? 0,
    };
  } catch {
    return null;
  }
}

export async function getAllQuotes(symbols: string[]): Promise<FinnhubQuote[]> {
  const results = await Promise.allSettled(symbols.map(getQuote));
  return results
    .filter((r) => r.status === 'fulfilled' && r.value !== null)
    .map((r) => (r as PromiseFulfilledResult<FinnhubQuote>).value);
}

/* ─── Financial Metrics API ─── */

export async function getBasicFinancials(symbol: string): Promise<FinnhubFinancials | null> {
  if (!FINNHUB_KEY) return null;
  try {
    // Finnhub basic financials endpoint (free tier)
    const res = await fetch(
      `https://finnhub.io/api/v1/stock/metric?symbol=${symbol}&metric=all&token=${FINNHUB_KEY}`
    );
    if (!res.ok) return null;
    const data = await res.json();
    const m = data.metric ?? {};

    return {
      symbol,
      peRatio:       m['peBasicExclExtraTTM']    ?? null,  // P/E ratio — already a ratio (e.g. 28.5)
      profitMargin:  m['netProfitMarginTTM']      ?? null,  // percentage (e.g. 25.31 = 25.31%)
      roe:           m['roeTTM']                  ?? null,  // percentage (e.g. 17.0 = 17%)
      revenueGrowth: m['revenueGrowthTTMYoy']     ?? null,  // percentage (e.g. 6.0 = 6%)
    };
  } catch {
    return null;
  }
}

/* ─── Helpers ─── */

export function isFinnhubConfigured(): boolean {
  return FINNHUB_KEY.length > 0;
}
