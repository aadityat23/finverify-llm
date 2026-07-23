<div align="center">

# FinVerify

**Verification-first financial AI. Deterministic correction instead of prompting or scale.**

[Live Demo](#) &nbsp;·&nbsp; [Documentation](finverify-terminal/README.md) &nbsp;·&nbsp; [Paper](#) &nbsp;·&nbsp; [Model](https://huggingface.co/aadi2026/finverify-lora)

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](finverify-terminal/backend/requirements.txt)
[![Next.js 14](https://img.shields.io/badge/next.js-14-black.svg)](finverify-terminal/frontend/package.json)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)
[![Discussions](https://img.shields.io/badge/GitHub-Discussions-informational.svg)](https://github.com/aadityat23/finverify-llm/discussions)

</div>

---

### Contents

[The problem](#the-problem) · [Results](#results) · [What is the DVL](#what-is-the-dvl) · [Features](#features) · [Screenshots](#screenshots) · [Quick start](#quick-start) · [Architecture](#architecture) · [Repository structure](#repository-structure) · [Benchmarks](#benchmarks) · [API reference](#api-reference) · [Research](#research) · [Roadmap](#roadmap) · [Contributing](#contributing) · [Community](#community) · [Contributors](#contributors) · [License](#license)

---

## The problem

LLMs answering financial questions are often directionally correct and numerically wrong — a decimal point misplaced, a percentage reported as a raw fraction, a sign flipped. In a regulated or capital-allocation context, that's not a rounding error, it's a liability.

Most fixes for this reach for more prompting: chain-of-thought, more context, bigger models. FinVerify takes a different approach. Formatting-level numerical errors — scale, sign, magnitude — are mechanically distinct from reasoning errors, and can be caught with a deterministic rule engine instead of another model call.

That's what the Deterministic Verification Layer (DVL) does. It doesn't make the model smarter. It catches the specific ways numerical output goes wrong, corrects them, and logs every correction so the output is auditable rather than opaque.

## Results

FinQA dev set, n=873, 95% bootstrap CI:

| Configuration | Accuracy | 95% CI | Δ |
|---|---|---|---|
| Baseline (no context) | 1.00% | [0.4, 1.9] | — |
| +Document Context | 24.00% | [21.2, 26.9] | +23.0pp |
| +DVL v1 | 32.00% | [29.0, 35.1] | +8.0pp |
| +QLoRA Fine-tuning | 38.50% | [35.4, 41.7] | +6.5pp |
| **+DVL v2 (final)** | **42.61%** | **[39.5, 45.7]** | **+4.1pp** |

Negative results: CoT prompting −9.0pp, CoT fine-tuning −12.0pp, cross-doc RAG −7.5pp.

At 42.61%, this is 5.4pp behind GPT-3.5 (no CoT, 48.0%) using a model 25x smaller, no proprietary compute, and fully deterministic, auditable output.

## What is the DVL

The Deterministic Verification Layer applies three ordered rules to LLM numerical output:

| Rule | Trigger | Example |
|---|---|---|
| Scale correction | Value <1 with percentage keyword | `0.1240` → `12.40%` |
| Sign correction | Correct magnitude, wrong sign | `−0.3411` → `+0.3411` |
| Magnitude correction | Wrong unit denomination | `104.0` → `1040.0 ≈ 995` |

Every correction is logged with rule type, original value, and corrected value. In regulated environments this audit trail is a compliance requirement, not a nicety.

Design constraint: the DVL only fires on formatting-level errors. It does not attempt to fix reasoning errors, which account for 73.1% of remaining failures. This boundary is enforced by design, not by omission.

## Features

**Verification Layer (DVL)**
Scale, sign, and magnitude correction on single numerical claims, with a full audit log per correction.

**Financial Constraint Graph (FCG)**
Checks relationships between multiple reported figures against accounting identities (gross profit = revenue − COGS, balance-sheet equation, EPS consistency), catching internally inconsistent output that single-number verification misses.

**Market Mode**
Live market data via Yahoo Finance. Derived metrics (P/E, margins, growth) run through the same DVL verification used for LLM output. Raw prices are never corrected, since they are ground truth by definition.

**Trust Engine**
Every verified value carries a HIGH / MEDIUM / LOW label, computed from the relative delta between raw and corrected values, not just a correction count.

**FinVerifyBench**
A synthetic diagnostic benchmark built to isolate formatting-level errors from reasoning errors, used to validate DVL behavior independent of any one model's reasoning quality.

**Audit logs**
Structured, per-correction logs (rule, input, output) for every value the DVL touches.

## Screenshots

Not yet included. If you'd like to contribute screenshots or a short recording of the terminal query flow, the market mode dashboard, or the correction-log animation, see [Contributing](#contributing) — this is a good self-contained first PR.

## Quick start

Clone the repository:

```bash
git clone https://github.com/aadityat23/finverify-llm.git
cd finverify-llm/finverify-terminal
```

Run the backend:

```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # fill in HF_TOKEN
uvicorn app.main:app --reload --port 8000
```

Run the frontend:

```bash
cd frontend
npm install
cp .env.local.example .env.local    # adjust API_URL if needed
npm run dev                          # http://localhost:3000
```

Verify the installation:

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/verify \
  -H "Content-Type: application/json" \
  -d '{"question": "What was the profit margin?", "raw_number": 0.1240}'

curl http://localhost:8000/market/quotes?symbols=AAPL,TSLA

curl "http://localhost:8000/market/verified-metrics?symbol=AAPL&metric=profit_margin"
```

The standalone SDK can be installed separately:

```bash
cd finverify-llm/finverify-terminal/sdk
pip install -e .
```

Use it to verify numbers locally with no network call, or against a hosted API. See `sdk/README.md` for usage.

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

This is the **core v1 verification pipeline**; it intentionally focuses on the DVL path and does not show the Financial Constraint Graph, SEC EDGAR/earnings-transcript ingestion, or RAG subsystems. Those are documented in the System Components table and [Repository structure](#repository-structure) below.

## Repository structure

```
finverify-llm/
├── README.md                    # this file
├── *.ipynb                      # research notebooks (FinQA experiments)
├── *.pdf                        # paper drafts and supplementary material
└── finverify-terminal/
    ├── backend/
    │   ├── app/
    │   │   ├── main.py          # FastAPI app and route definitions
    │   │   ├── dvl.py           # Deterministic Verification Layer
    │   │   ├── router.py        # numerical vs advisory query classifier
    │   │   ├── parser.py        # numeric extraction from LLM text
    │   │   ├── market.py        # yfinance wrapper, DVL-verified metrics
    │   │   └── models.py        # request/response schemas
    │   ├── fcg/                 # Financial Constraint Graph, metric normalizer
    │   ├── ingestion/           # SEC EDGAR and earnings-transcript ingestion
    │   ├── rag/                 # retrieval pipeline (Pinecone + fallback search)
    │   └── evals/               # cross-model evaluation harness
    ├── frontend/
    │   ├── app/                 # Next.js pages: terminal, market, metrics
    │   ├── components/          # TrustScore, DVLReport, VerificationLog, etc.
    │   └── lib/                 # API client, offline DVL fallback, history
    └── sdk/
        └── finverify/           # standalone `pip install finverify` package
```

| Component | Path | Purpose |
|---|---|---|
| DVL engine | `backend/app/dvl.py` | Scale/sign/magnitude correction with audit logging |
| Query classifier | `backend/app/router.py` | Routes numerical vs advisory queries |
| Market layer | `backend/app/market.py` | Live yfinance data, DVL-verified financial metrics |
| Financial Constraint Graph | `backend/fcg/constraint_engine.py` | Multi-number accounting-identity and ratio-bound checks |
| SEC EDGAR ingestion | `backend/ingestion/sec_edgar.py` | XBRL/fallback ingestion of 10-K/10-Q fundamentals |
| Earnings transcript verification | `backend/ingestion/transcripts.py` | Regex extraction and DVL verification of earnings-call claims |
| RAG pipeline | `backend/rag/pipeline.py` | Pinecone vector + keyword-overlap fallback retrieval |
| WebSocket server | `backend/app/main.py` | Real-time market data push (5s interval) |
| Terminal UI | `frontend/app/page.tsx` | Terminal-style query interface, three-panel layout |
| Market mode | `frontend/app/market/page.tsx` | Live watchlist, verified metric cards, sparklines |
| Metrics dashboard | `frontend/app/metrics/page.tsx` | Paper results, ablation study, error taxonomy |

## Benchmarks

FinQA dev set, n=873, 95% bootstrap CI:

| Configuration | Accuracy | 95% CI | Δ |
|---|---|---|---|
| Baseline (no context) | 1.00% | [0.4, 1.9] | — |
| +Document Context | 24.00% | [21.2, 26.9] | +23.0pp |
| +DVL v1 | 32.00% | [29.0, 35.1] | +8.0pp |
| +QLoRA Fine-tuning | 38.50% | [35.4, 41.7] | +6.5pp |
| **+DVL v2 (final)** | **42.61%** | **[39.5, 45.7]** | **+4.1pp** |

Negative results: CoT prompting −9.0pp, CoT fine-tuning −12.0pp, cross-doc RAG −7.5pp.

### Error taxonomy (n=539 remaining failures)

| Error type | Count | % |
|---|---|---|
| Reasoning (close, <50% rel.) | 210 | 39.0% |
| Reasoning (far, >50% rel.) | 184 | 34.1% |
| Magnitude | 66 | 12.2% |
| Order-of-magnitude | 62 | 11.4% |
| Sign | 9 | 1.6% |
| Scale | 4 | 0.8% |

73.1% of remaining failures are reasoning errors, not correctable by the DVL. 0% are formatting or extraction failures after fine-tuning.

## API reference

| Method | Path | Description |
|---|---|---|
| POST | `/query` | LLM inference + DVL verification |
| POST | `/verify` | DVL-only verification, no LLM call |
| GET | `/health` | Health check |
| GET | `/market/quotes?symbols=AAPL,TSLA` | Live stock quotes |
| GET | `/market/indices` | S&P 500, NASDAQ, VIX |
| GET | `/market/verified-metrics?symbol=AAPL&metric=profit_margin` | DVL-verified metric |
| GET | `/market/all-metrics?symbol=AAPL` | All five metrics for a symbol |
| POST, GET | `/v1/fcg/*` | FCG endpoints: verify, normalize, list constraints |
| POST, GET | `/v1/rag/*` | RAG endpoints: query, stats, seed |
| GET, POST, DELETE | `/v1/history/*` | User query-history persistence |
| WS | `/ws/market` | Real-time market data stream |

The backend also exposes `/v1/fundamentals/{ticker}`, `/v1/earnings/{ticker}`, and `/v1/ingest/*` routes for on-demand SEC and transcript ingestion. Endpoint-by-endpoint documentation for these is an open contribution opportunity — see [Contributing](#contributing).

## Research

**Paper** — *Modular Verification Outperforms Chain-of-Thought Reasoning in Small Financial LLMs: A Systematic Ablation Study on Numerical Hallucination Reduction*

**Submitted to** — FinNLP @ EMNLP 2026 / IEEE Access

**Author** — Aaditya Thokal, Universal College of Engineering, Mumbai — [aaditya.thokal24@gmail.com](mailto:aaditya.thokal24@gmail.com)

**Model** — [aadi2026/finverify-lora](https://huggingface.co/aadi2026/finverify-lora), Mistral-7B + QLoRA, trained on 2,000 FinQA examples

**Dataset** — evaluated on the [FinQA](https://finqasite.github.io/) dev set (n=873). FinVerifyBench, a synthetic diagnostic benchmark, is used to isolate formatting-level errors from reasoning errors.

## Roadmap

Development is tracked through GitHub Milestones.

Current priorities include:

- Consolidating the verification engine
- Expanding automated test coverage
- Improving API stability
- Extending benchmark coverage
- Enhancing developer experience
- Strengthening documentation

Future work includes broader model evaluation, improved deployment tooling, and additional verification methods.

## Contributing

Start with [CONTRIBUTING.md](./CONTRIBUTING.md) for setup, workflow, and coding standards.

Issues labeled `good first issue` are self-contained and don't require deep familiarity with the DVL or FCG internals. Larger or research-oriented work is labeled `advanced` or `research`.

Please also read the [Code of Conduct](./CODE_OF_CONDUCT.md).

## Community

| | |
|---|---|
| Website | [Live Demo](#) |
| Discussions | [GitHub Discussions](https://github.com/aadityat23/finverify-llm/discussions) — design questions, feedback, "is this worth doing" conversations |
| Issues | [GitHub Issues](https://github.com/aadityat23/finverify-llm/issues) — bugs and tracked work |
| Contributing guide | [CONTRIBUTING.md](./CONTRIBUTING.md) |

## Contributors

FinVerify was created and is currently maintained by [Aaditya Thokal](mailto:aaditya.thokal24@gmail.com), Universal College of Engineering, Mumbai.

The project is early enough that this list is short. If you contribute a merged PR, you belong here — open a PR adding yourself once it lands.

## License

Apache License 2.0. See [LICENSE](./LICENSE).

---

<div align="center">

If FinVerify is useful to you, consider starring the repository.

</div>
