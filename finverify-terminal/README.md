# FinVerify Terminal

[![Live Demo](https://img.shields.io/badge/DEMO-finverify--llm.vercel.app-00ff88?style=for-the-badge&logo=vercel)](https://finverify-llm.vercel.app)
[![HuggingFace](https://img.shields.io/badge/🤗_Model-aadi2026/finverify--lora-yellow?style=for-the-badge)](https://huggingface.co/aadi2026/finverify-lora)
[![API](https://img.shields.io/badge/API-HuggingFace_Spaces-blue?style=for-the-badge)](https://aadi2026-finverify-api.hf.space/health)

> Verification-first financial AI system. Reduces numerical hallucination in LLMs through deterministic correction, achieving **42× accuracy improvement** on FinQA benchmark.

---

## 🎯 Live Demo

**→ [finverify-llm.vercel.app](https://finverify-llm.vercel.app)**

### Demo Walkthrough

**1. Empty Terminal — DVL Explainer**
The landing page shows how the 3 DVL rules work with visual pill-style examples:
```
[SCALE: 0.12 → 12%]  [SIGN: -0.34 → +0.34]  [MAGNITUDE: 104 → 1040]
```

**2. Query: "HTM securities decrease?"**
Type the query or click from sample queries. The DVL correction log animates in real-time:
```
[00:00:001] INPUT    -34.11
[00:00:002] KEYWORD  "decrease" → RATIO
[00:00:003] RULE     scale_div100
                     IN:  -34.11
                     OUT: -0.3411
[00:00:004] DONE     CORRECTED
```

**3. Verified Output with Pipeline**
The compound correction chain is visualized:
```
RAW: -34.11 ──[scale_div100]──▸ VERIFIED: -0.3411
```
Trust badge shows **MEDIUM** (amber) — hover it to see explanations.

**4. Market Mode (Finnhub Live Data)**
Click MARKET tab for real-time stock data with DVL-verified financial metrics:
```
PROFIT MARGIN    ROE             P/E RATIO       REVENUE GROWTH
RAW: 0.2715      RAW: 1.4669     RAW: 36.53      RAW: 0.1276
VERIFIED: 27.15%  VERIFIED: 1.47%  VERIFIED: 36.53×  VERIFIED: 12.76%
RULE: SCALE_MUL100  RULE: NO CORRECTION  RULE: NO CORRECTION  RULE: SCALE_MUL100
TRUST: MEDIUM     TRUST: HIGH      TRUST: HIGH      TRUST: MEDIUM
```

---

## Results (FinQA Dev Set, n=873, 95% Bootstrap CI)

| Configuration | Accuracy | 95% CI | Δ |
|---|---|---|---|
| Baseline (no context) | 1.00% | [0.4, 1.9] | — |
| +Document Context | 24.00% | [21.2, 26.9] | +23.0pp |
| +DVL v1 | 32.00% | [29.0, 35.1] | +8.0pp |
| +QLoRA Fine-tuning | 38.50% | [35.4, 41.7] | +6.5pp |
| **+DVL v2 (final)** | **42.61%** | **[39.5, 45.7]** | **+4.1pp** |

**Negative results:** CoT prompting −9.0pp · CoT fine-tuning −12.0pp · Cross-doc RAG −7.5pp

Approaches GPT-3.5 (no CoT) at 42.61% vs 48.0% — 5.4pp gap with a model **25× smaller**, zero proprietary compute, and fully deterministic auditable outputs.

---

## What is the DVL?

The **Deterministic Verification Layer** applies three ordered rules to LLM numerical outputs:

| Rule | Trigger | Example | Trust |
|---|---|---|---|
| **Scale correction** | Value <1 with percentage keyword | `0.1240` → `12.40%` | MEDIUM |
| **Sign correction** | Correct magnitude, wrong sign | `−0.3411` → `+0.3411` | MEDIUM |
| **Magnitude correction** | Wrong unit denomination | `104.0` → `1040.0 ≈ 995` | LOW |

Every correction is logged with rule type, original value, corrected value. In regulated environments, this audit trail is a compliance requirement.

**Key design constraint:** DVL only fires on formatting-level errors. It does not attempt to fix reasoning errors (73.1% of remaining failures). This boundary is enforced by design.

---

## Architecture

```
User Query
    │
    ▼
┌─────────────────┐
│ Query Classifier │──── advisory ────► LLM Only → Unverified Response
└────────┬────────┘
         │ numerical
         ▼
┌─────────────────┐     ┌──────────────────────────┐
│   LLM Inference  │────►│  DVL Pipeline             │
│  (Mistral-7B +   │     │  scale → sign → magnitude │
│   QLoRA)         │     │  + audit log per step      │
└─────────────────┘     └────────────┬─────────────┘
                                     │
                                     ▼
                        ┌──────────────────────────┐
                        │  Trust Engine              │
                        │  HIGH / MEDIUM / LOW       │
                        │  (delta-based scoring)     │
                        └────────────┬─────────────┘
                                     │
                                     ▼
                              Verified Output
                         + correction log + trust
```

---

## Error Taxonomy (n=539 remaining failures)

| Error Type | Count | % |
|---|---|---|
| Reasoning (close, <50% rel.) | 210 | 39.0% |
| Reasoning (far, >50% rel.) | 184 | 34.1% |
| Magnitude | 66 | 12.2% |
| Order-of-magnitude | 62 | 11.4% |
| Sign | 9 | 1.6% |
| Scale | 4 | 0.8% |

73.1% of failures are reasoning errors — not correctable by the DVL.  
0% are formatting/extraction failures after fine-tuning.

---

## System Components

| Component | Path | Purpose |
|---|---|---|
| DVL Engine | `backend/app/dvl.py` | Scale/sign/magnitude correction with full audit logging |
| Query Classifier | `backend/app/router.py` | Routes numerical vs advisory queries |
| Market Layer | `backend/app/market.py` | Live yfinance data + DVL-verified financial metrics |
| V1 API | `backend/app/main.py` | Standalone `/v1/verify` REST endpoint |
| Terminal UI | `frontend/app/page.tsx` | Bloomberg-style dark terminal, 3-panel layout |
| Market Mode | `frontend/app/market/page.tsx` | Live Finnhub watchlist, DVL-verified metric cards |
| Metrics Dashboard | `frontend/app/metrics/page.tsx` | Full paper results, ablation study, error taxonomy |
| Market Data | `frontend/lib/market.ts` | Finnhub integration for live quotes + financials |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/verify` | **Standalone DVL API** — verify any financial number |
| POST | `/query` | LLM inference + DVL verification |
| POST | `/verify` | DVL-only verification (no LLM call) |
| GET | `/health` | Health check |
| GET | `/market/quotes?symbols=AAPL,TSLA` | Live stock quotes |
| GET | `/market/indices` | S&P 500, NASDAQ, VIX |
| GET | `/market/all-metrics?symbol=AAPL` | All 5 DVL-verified metrics for a symbol |

### Standalone DVL API (`/v1/verify`)

Any application can verify financial numbers through the DVL:

```bash
curl -X POST https://aadi2026-finverify-api.hf.space/v1/verify \
  -H "Content-Type: application/json" \
  -H "X-FinVerify-Key: your-optional-key" \
  -d '{"question": "What was the profit margin?", "raw_value": 0.2531}'
```

Response:
```json
{
  "question": "What was the profit margin?",
  "raw_value": 0.2531,
  "verified_value": 25.31,
  "correction_applied": "scale_mul100",
  "trust_score": "MEDIUM",
  "trust_color": "#fbbf24",
  "delta_pct": 9902.7678,
  "dvl_version": "1.0.0",
  "timestamp": "2026-05-22T12:00:00+00:00"
}
```

Rate limit: 100 requests/minute per IP.

---

## Research

**Paper:** *Modular Verification Outperforms Chain-of-Thought Reasoning in Small Financial LLMs: A Systematic Ablation Study on Numerical Hallucination Reduction*

**Submitted to:** FinNLP @ EMNLP 2026 / IEEE Access

**Author:** Aaditya Thokal · Universal College of Engineering, Mumbai · aaditya.thokal24@gmail.com

**Model:** [aadi2026/finverify-lora](https://huggingface.co/aadi2026/finverify-lora) — Mistral-7B + QLoRA, trained on 2,000 FinQA examples

**Citation:**
```bibtex
@article{thokal2026finverify,
  title={Modular Verification Outperforms Chain-of-Thought Reasoning in Small Financial LLMs:
         A Systematic Ablation Study on Numerical Hallucination Reduction},
  author={Thokal, Aaditya},
  year={2026},
  institution={Universal College of Engineering, Mumbai},
  note={FinQA dev set, n=873, 42.61\% accuracy with 95\% bootstrap CI [39.5, 45.7]}
}
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, Tailwind CSS, Recharts, JetBrains Mono |
| Backend | FastAPI, Python 3.11, uvicorn, slowapi |
| Model | Mistral-7B-Instruct v0.2 + QLoRA (4-bit NF4) |
| Market Data | Finnhub (frontend) + yfinance (backend) |
| Deploy | Vercel (frontend) + HuggingFace Spaces (backend) |

---

## Local Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # fill in HF_TOKEN
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
# Set NEXT_PUBLIC_FINNHUB_KEY for live market data
npm run dev                          # → http://localhost:3000
```

### Environment Variables

| Variable | Where | Purpose |
|---|---|---|
| `HF_TOKEN` | Backend `.env` | HuggingFace API token for LLM inference |
| `NEXT_PUBLIC_API_URL` | Frontend `.env.local` | Backend API URL |
| `NEXT_PUBLIC_FINNHUB_KEY` | Frontend `.env.local` | Finnhub API key for live market data |

### Verify

```bash
# Health check
curl http://localhost:8000/health

# DVL verification (standalone API)
curl -X POST http://localhost:8000/v1/verify \
  -H "Content-Type: application/json" \
  -d '{"question": "What was the profit margin?", "raw_value": 0.1240}'

# DVL verification (internal)
curl -X POST http://localhost:8000/verify \
  -H "Content-Type: application/json" \
  -d '{"question": "What was the profit margin?", "raw_number": 0.1240}'

# Run API test suite
python test_verify_api.py
python test_verify_api.py https://aadi2026-finverify-api.hf.space
```

---

## License

MIT

---

*Built by Aaditya Thokal — Universal College of Engineering, Mumbai*
