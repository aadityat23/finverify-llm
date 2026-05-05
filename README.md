# FinVerify Terminal

> Verification-first financial AI system. Reduces numerical hallucination in LLMs through deterministic correction, achieving **42× accuracy improvement** on FinQA benchmark.

**[Live Demo](#) · [HuggingFace Model](https://huggingface.co/aadi2026/finverify-lora) · [Research Paper](#) · [Author](mailto:aaditya.thokal24@gmail.com)**

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

| Rule | Trigger | Example |
|---|---|---|
| Scale correction | Value <1 with percentage keyword | `0.1240` → `12.40%` |
| Sign correction | Correct magnitude, wrong sign | `−0.3411` → `+0.3411` |
| Magnitude correction | Wrong unit denomination | `104.0` → `1040.0 ≈ 995` |

Every correction is logged with rule type, original value, corrected value. In regulated environments, this audit trail is a compliance requirement.

**Key design constraint:** DVL only fires on formatting-level errors. It does not attempt to fix reasoning errors (73.1% of remaining failures). This boundary is enforced by design.

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

## System Components

| Component | Path | Purpose |
|---|---|---|
| DVL Engine | `backend/app/dvl.py` | Scale/sign/magnitude correction with full audit logging |
| Query Classifier | `backend/app/router.py` | Routes numerical vs advisory queries |
| Market Layer | `backend/app/market.py` | Live yfinance data + DVL-verified financial metrics |
| WebSocket Server | `backend/app/main.py` | Real-time market data push (5s interval) |
| Terminal UI | `frontend/app/page.tsx` | Bloomberg-style dark terminal, 3-panel layout |
| Market Mode | `frontend/app/market/page.tsx` | Live watchlist, DVL-verified metric cards, sparklines |
| Metrics Dashboard | `frontend/app/metrics/page.tsx` | Full paper results, ablation study, error taxonomy |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/query` | LLM inference + DVL verification |
| POST | `/verify` | DVL-only verification (no LLM call) |
| GET | `/health` | Health check |
| GET | `/market/quotes?symbols=AAPL,TSLA` | Live stock quotes |
| GET | `/market/indices` | S&P 500, NASDAQ, VIX |
| GET | `/market/verified-metrics?symbol=AAPL&metric=profit_margin` | DVL-verified metric |
| GET | `/market/all-metrics?symbol=AAPL` | All 5 metrics for a symbol |
| WS | `/ws/market` | Real-time market data stream |

---

## Research

**Paper:** *Modular Verification Outperforms Chain-of-Thought Reasoning in Small Financial LLMs: A Systematic Ablation Study on Numerical Hallucination Reduction*

**Submitted to:** FinNLP @ EMNLP 2026 / IEEE Access

**Author:** Aaditya Thokal · Universal College of Engineering, Mumbai · aaditya.thokal24@gmail.com

**Model:** [aadi2026/finverify-lora](https://huggingface.co/aadi2026/finverify-lora) — Mistral-7B + QLoRA, trained on 2,000 FinQA examples

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, Tailwind CSS, Recharts, JetBrains Mono |
| Backend | FastAPI, Python 3.11, uvicorn |
| Model | Mistral-7B-Instruct v0.2 + QLoRA (4-bit NF4) |
| Market Data | yfinance (Yahoo Finance unofficial API) |
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
cp .env.local.example .env.local    # adjust API_URL if needed
npm run dev                          # → http://localhost:3000
```

### Verify

```bash
# Health check
curl http://localhost:8000/health

# DVL verification
curl -X POST http://localhost:8000/verify \
  -H "Content-Type: application/json" \
  -d '{"question": "What was the profit margin?", "raw_number": 0.1240}'

# Market quotes
curl http://localhost:8000/market/quotes?symbols=AAPL,TSLA

# DVL-verified metric
curl "http://localhost:8000/market/verified-metrics?symbol=AAPL&metric=profit_margin"
```

---

## License

MIT

---

*Built by Aaditya Thokal — Universal College of Engineering, Mumbai*
