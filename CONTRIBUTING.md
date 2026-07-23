# Contributing to FinVerify

## Welcome

FinVerify is an open-source platform building trustworthy financial AI infrastructure through **deterministic verification** and **reproducible evaluation**. Large language models are increasingly used to answer financial questions, but they routinely get the *arithmetic* right in spirit and wrong in the details — a decimal point in the wrong place, a percentage reported as a raw fraction, a sign flipped. FinVerify's core idea is that these formatting-level failures are structurally different from reasoning failures, and can be caught deterministically rather than papered over with more prompting.

That idea shows up across the project as a few concrete systems:

- The **Deterministic Verification Layer (DVL)** — rule-based scale, sign, and magnitude correction for single numerical claims.
- The **Financial Constraint Graph (FCG)** — accounting-identity and ratio-bound checks across *multiple* related numbers.
- A **verification pipeline** that ties LLM inference, ingestion (SEC EDGAR filings, earnings transcripts), and retrieval together behind a FastAPI backend, a Next.js terminal-style frontend, and a standalone `finverify` Python SDK.
- A **research track** producing benchmarks (FinVerifyBench), reproducible evaluation numbers on FinQA, and published error taxonomies.

We welcome contributors at every level of experience — from a first-time open-source contributor fixing a stray file or writing a test, to an ML researcher who wants to argue with our benchmark methodology. If you're comfortable reading Python or TypeScript, there's a place for you here. If you're not sure where to start, read [Choosing an Issue](#choosing-an-issue) below and open a Discussion — we'd rather help you find the right first issue than have you guess.

---

## Ways to Contribute

You don't need to touch the DVL's correction logic to make a meaningful contribution. FinVerify currently needs help across:

- **Backend Engineering** — the FastAPI service in `finverify-terminal/backend`: the DVL and FCG engines, market data, SEC/earnings ingestion, the RAG pipeline, and the API surface itself.
- **Frontend Engineering** — the Next.js terminal UI in `finverify-terminal/frontend`: the query terminal, the live market dashboard, and the metrics/paper dashboard.
- **Machine Learning** — the fine-tuned Mistral-7B-Instruct + QLoRA model, prompt/generation behavior, and the cross-model evaluation harness comparing DVL's effect across different LLMs.
- **Data Engineering** — SEC EDGAR XBRL ingestion, earnings-transcript claim extraction, and the SQLite/Pinecone storage layers underneath them.
- **Research** — FinVerifyBench, DVL/FCG methodology, error-taxonomy analysis, and reproducing the paper's reported results from the shipped codebase rather than only the research notebooks.
- **Documentation** — keeping the README, SDK docs, and architecture explanations honest about what the code actually does today.
- **Testing** — the project currently has real but thin test coverage (DVL correctness tests exist; most other subsystems don't have any yet). This is one of the highest-leverage ways to contribute right now.
- **UI/UX** — trust-signal clarity (e.g., making sure a user can tell a verified value from an unverifiable one), error states, and the terminal aesthetic.

---

## Development Setup

FinVerify's application code lives under `finverify-terminal/` inside the repository (the repo root also holds the research notebooks and paper drafts — see [Repository Structure](#repository-structure)).

### Clone the repository

```bash
git clone https://github.com/aadityat23/finverify-llm.git
cd finverify-llm/finverify-terminal
```

### Backend (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # fill in HF_TOKEN at minimum; other keys are optional
uvicorn app.main:app --reload --port 8000
```

The backend degrades gracefully if optional services aren't configured — Pinecone (RAG), Supabase (query history), and Finnhub are all optional. `HF_TOKEN` is required for live LLM inference against the fine-tuned model; without it, `/verify` (DVL-only, no LLM call) still works.

### Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.local.example .env.local    # adjust NEXT_PUBLIC_API_URL if pointing at local backend
npm run dev                          # → http://localhost:3000
```

By default, `.env.local.example` points `NEXT_PUBLIC_API_URL` at the hosted HuggingFace Space demo API. If you're working on backend changes, point it at your local `http://localhost:8000` instead. Clerk authentication is optional in local dev — the app runs in anonymous mode if `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` isn't set.

### SDK (`finverify` Python package)

```bash
cd sdk
pip install -e .
python -m tests.test_dvl
```

### Running tests

The project's test suites are currently standalone scripts rather than a pytest suite (this is itself a good first issue — see [Choosing an Issue](#choosing-an-issue)). Run them directly:

```bash
# Backend: DVL engine unit tests
cd backend
python test_dvl.py

# Backend: live API tests (requires the backend running on :8000 in another terminal)
python test_verify_api.py

# SDK: local DVL tests
cd sdk
python tests/test_dvl.py
```

There is currently no CI pipeline running these automatically on pull requests — please run the relevant suite(s) locally before opening a PR, and mention the results in your PR description.

---

## Repository Structure

```
finverify-llm/
├── README.md                              # Project overview, results, architecture
├── *.ipynb                                # Research notebooks (FinQA experiments)
├── *.pdf                                  # Paper drafts / supplementary material
└── finverify-terminal/
    ├── README.md                          # Full product README (demo walkthrough, API docs)
    ├── backend/
    │   ├── app/
    │   │   ├── main.py                    # FastAPI app and route definitions
    │   │   ├── dvl.py                     # Deterministic Verification Layer (core algorithm)
    │   │   ├── router.py                  # Keyword-based query classifier
    │   │   ├── parser.py                  # Numeric extraction from LLM text
    │   │   ├── market.py                  # yfinance wrapper + cache for live market data
    │   │   ├── evaluator.py               # Orchestrates parser + DVL + response building
    │   │   ├── models.py                  # Pydantic request/response schemas
    │   │   └── supabase_client.py         # Optional query-history persistence
    │   ├── fcg/
    │   │   ├── constraint_engine.py       # Financial Constraint Graph (accounting-identity checks)
    │   │   └── normalizer.py              # Metric-name alias matching (exact + fuzzy)
    │   ├── ingestion/
    │   │   ├── sec_edgar.py               # SEC EDGAR XBRL fetching + fallback filings data
    │   │   ├── transcripts.py             # Earnings-call claim extraction (sample transcripts)
    │   │   └── db.py                      # SQLite storage for fundamentals + transcript claims
    │   ├── rag/
    │   │   ├── pipeline.py                # Pinecone-backed retrieval with keyword-overlap fallback
    │   │   └── seed.py                    # Seeds the RAG index from SQLite data
    │   ├── evals/
    │   │   └── cross_model_eval.py        # Compares DVL's effect across Mistral/GPT/Claude
    │   ├── test_dvl.py                    # DVL correctness tests
    │   └── test_verify_api.py             # Live-server API tests
    ├── frontend/
    │   ├── app/                           # Next.js App Router pages (terminal, market, metrics)
    │   ├── components/                    # TrustScore, DVLReport, VerificationLog, Watchlist, etc.
    │   └── lib/                           # api.ts (backend client), dvl.ts (offline fallback), history.ts
    └── sdk/
        └── finverify/
            ├── dvl.py                     # Standalone DVL implementation for pip install finverify
            ├── client.py                  # HTTP client for the hosted/local API
            └── interceptor.py             # Wraps OpenAI-style LLM calls with auto-verification
```

If you're not sure which layer a change belongs in: DVL logic (single-number correction) lives in **three places** today — `backend/app/dvl.py`, `sdk/finverify/dvl.py`, and `frontend/lib/dvl.ts` (a simplified offline fallback). If you're fixing a DVL bug, check whether it needs to be fixed in more than one of these — this is a known area of technical debt we're actively working to consolidate.

---

## Choosing an Issue

Every issue in the tracker is labeled to help you find something matched to your interests and available time. Here's what each label means in this repository:

| Label | Meaning |
|---|---|
| `good first issue` | Self-contained, doesn't require deep familiarity with the DVL/FCG internals, and has a clear, narrow acceptance criteria. Great for your first PR. |
| `intermediate` | Requires reading and understanding an existing module in depth (e.g., the constraint engine or the ingestion pipeline) before changing it. |
| `advanced` | Touches core algorithms, cross-cutting concerns across backend/SDK/frontend, or has real design decisions to make — expect some back-and-forth with a maintainer before landing. |
| `help wanted` | A maintainer has flagged this as something we specifically want outside contribution on, regardless of difficulty. |
| `backend` | Python / FastAPI service code under `finverify-terminal/backend`. |
| `frontend` | Next.js / TypeScript code under `finverify-terminal/frontend`. |
| `testing` | Adding or improving test coverage. Given how thin coverage currently is outside the DVL engine, these issues are consistently high-impact. |
| `security` | Auth, CORS, secrets handling, or anything with a trust/safety implication. These are treated as high priority regardless of difficulty rating. |
| `research` | Benchmark methodology, evaluation reproducibility, error-taxonomy analysis, or anything tied to the paper's claims. |
| `documentation` | READMEs, SDK docs, inline comments, architecture write-ups. |
| `api` | Changes to request/response contracts on any `/query`, `/verify`, or `/v1/*` endpoint — these get extra scrutiny since they can break existing consumers (the web app, the SDK, and direct API users). |
| `refactor` | Restructuring existing code without changing behavior — the acceptance criteria will almost always include "no behavior change," verified by existing tests passing unmodified. |
| `priority:high` | A maintainer has assessed this as blocking, safety-relevant, or foundational to other work — these get prioritized in review. |

If an issue has no assignee and you'd like to work on it, comment on it before starting so we don't end up with duplicate work. If you're picking up your first issue here, `good first issue` + `backend` or `good first issue` + `documentation` are the lowest-friction combinations to start with.

---

## Development Workflow

1. **Fork the repository** and clone your fork locally.
2. **Create a feature branch** off `main` — name it descriptively (e.g., `fix/cors-wildcard-origin`, `test/fcg-constraint-engine`).
3. **Implement your changes**, following the [Coding Standards](#coding-standards) below.
4. **Run the relevant test suite(s)** locally (see [Development Setup](#development-setup)) and confirm they pass.
5. **Open a Pull Request** against `main`, filling out the PR description (link the issue you're resolving, summarize what changed and why).
6. **Wait for review.** A maintainer will review, may ask for changes, and will merge once the PR meets the checklist below. Please be patient — this is a small maintainer team.

---

## Coding Standards

- **Follow existing project style.** Backend Python follows the conventions already established in `dvl.py`, `constraint_engine.py`, and `main.py` — type hints on function signatures, module-level docstrings explaining intent, and inline comments explaining *why* a design decision was made (not just what the code does). Frontend TypeScript follows the existing component structure in `frontend/components/`.
- **Keep PRs focused.** One issue, one concern, one PR. A PR that fixes a bug and also reformats an unrelated file is harder to review and harder to revert if something goes wrong. If you notice something else worth fixing while you're in a file, open a separate issue for it rather than bundling it in.
- **Write clear commit messages.** Describe *what* changed and, where it's not obvious, *why*. `Fix CORS wildcard origin` is better than `fix bug`.
- **Add tests whenever appropriate.** If you're fixing a bug, add a test that would have caught it. If you're adding a feature to a module that has existing tests (like `dvl.py`), extend that suite rather than starting a parallel one.
- **Update documentation when behavior changes.** If your PR changes an API response shape, a setup step, or a default, update the relevant README or docstring in the same PR — don't leave it for someone else to notice the drift later.
- **Respect the DVL's design boundary.** The DVL is intentionally scoped to formatting-level corrections (scale, sign, magnitude) and explicitly does not attempt to fix reasoning errors. If your change would blur that boundary, raise it as a design discussion first rather than assuming it's an oversight.

---

## Pull Request Checklist

Before requesting review, confirm:

- [ ] Code builds and runs successfully locally (backend starts with `uvicorn app.main:app --reload`, frontend builds with `npm run build` if you touched frontend code)
- [ ] Relevant test suite(s) pass locally (`python test_dvl.py`, `python test_verify_api.py`, and/or `python tests/test_dvl.py` in `sdk/`, as applicable to your change)
- [ ] New tests are included for new behavior or bug fixes
- [ ] Documentation (README, docstrings, SDK docs) is updated if behavior, setup steps, or API contracts changed
- [ ] No unnecessary files are included (no `.env`, `venv/`, `node_modules/`, `__pycache__/`, or editor config files)
- [ ] The PR description references the issue it resolves (e.g., `Closes #42`)
- [ ] If the change touches DVL logic, you've checked whether `backend/app/dvl.py`, `sdk/finverify/dvl.py`, and `frontend/lib/dvl.ts` need corresponding updates

---

## Reporting Bugs

A useful bug report lets a maintainer reproduce the problem without back-and-forth. Please include:

- **What you did** — the exact request, query, or steps taken (e.g., "Called `POST /v1/verify` with this payload...").
- **What you expected** vs. **what actually happened**, including the full response or error message where relevant.
- **Which surface** you were using — the web app (finverify-llm.vercel.app or local), a direct API call, or the Python SDK — since behavior can currently differ across these (see the DVL triplication note above).
- **Environment details** if it's a local setup issue: OS, Python version, Node version, and whether you're running against the hosted API or a local backend.
- **Whether it involves a specific ticker or dataset**, since some ingestion features (SEC EDGAR fundamentals, earnings transcripts) currently only cover a fixed set of tickers — if your report involves a ticker outside that set, say so, since the expected behavior may differ.

If you're reporting a security issue (auth, CORS, secrets exposure), please see the note in [Community](#community) below rather than opening a public issue.

---

## Feature Requests

We're happy to consider feature requests, but please frame them around a concrete problem rather than a solution, so we can evaluate whether it fits FinVerify's scope (verification and evaluation of financial numerical output, not general-purpose financial advice or portfolio management). Before opening one:

- Check whether an existing issue already covers it.
- Explain the problem you're hitting, not just the feature you want — "I can't tell whether a `HIGH` trust value was actually verified or just passed through unmodified" is more actionable than "add better trust scores."
- If the feature would change an existing API contract or the DVL's correction behavior, expect a design discussion before implementation begins — these changes affect every consumer (web app, SDK, direct API users) at once.

---

## Research Contributions

FinVerify's research surface is as open to contribution as the code. If you want to work on the underlying methodology rather than the application layer, here's where that work lives:

- **DVL** (`backend/app/dvl.py`) — the deterministic correction rules themselves. Contributions here should come with test cases demonstrating the specific failure mode being addressed, and should respect the existing scale/sign/magnitude boundary rather than expanding DVL into reasoning-correction territory.
- **Financial Constraint Graph** (`backend/fcg/constraint_engine.py`) — the hard and soft accounting-identity constraints. If you have a financial identity or ratio bound you think is missing, or believe an existing tolerance is miscalibrated, open an issue with your reasoning and, ideally, real-world figures that demonstrate it.
- **Verification pipeline** — how DVL, the FCG, ingestion, and RAG compose together. Several of these are currently wired as independent stages rather than a single enforced pipeline (for example, the FCG's own documentation describes DVL as a required first pass, but the live API doesn't currently enforce that order) — closing gaps like this is valuable research-adjacent engineering work.
- **Benchmarks** — FinVerifyBench and its construction. If you find a defect in the benchmark data (empty tables, samples with operands missing from context, truncation issues), that's a legitimate and valuable finding — please open an issue with the specific sample.
- **Evaluation** — reproducing the paper's reported FinQA results (42.61% accuracy, n=873) from the *shipped* backend code, rather than only from the research notebooks, is one of the most valuable things a research-minded contributor could currently do. If you can reproduce it, that closes an important gap. If you can't, that's equally valuable information — open an issue documenting exactly where the divergence appears.

If your contribution would materially affect a claim made in the published paper or the README's results table, please flag that explicitly in your PR so it gets appropriate review before merging.

---

## Community

FinVerify is maintained by a small team and grows through contributors who bring both code and scrutiny — including scrutiny of our own benchmark claims and design decisions. Please engage respectfully: disagree with a design decision or a reviewer's comment on its merits, assume good faith, and remember that a "no" or "not yet" on a PR is about scope and timing, not a judgment of the contributor.

We welcome open discussion and feedback, including on things we've clearly gotten wrong (and there are several documented in our own architecture notes — inconsistent defaults between the SDK and the web app, duplicated logic across implementations, thin test coverage in places). Pointing these out, or better, opening a PR to fix them, is exactly the kind of contribution this project needs.

If you believe you've found a security-sensitive issue (authentication, CORS, secrets handling, or anything that could expose user or query data), please reach out directly to the maintainer by email rather than opening a public issue, so it can be addressed before details are public.

---

## Questions

- **GitHub Discussions** — the best place for open-ended questions, design discussions, and "is this worth doing" conversations before you invest time in a PR.
- **GitHub Issues** — for concrete bugs, well-scoped feature requests, and tracked work items (see [Choosing an Issue](#choosing-an-issue)).
- **Website / Live Demo** — [finverify-llm.vercel.app](https://finverify-llm.vercel.app) to see the current state of the product before proposing changes to it.
- **Founder contact** — [aaditya.thokal24@gmail.com](mailto:aaditya.thokal24@gmail.com) for anything sensitive, security-related, or not suited to a public thread.

Thank you for considering a contribution to FinVerify — verification-first financial AI is a small niche today, and every fixed test gap, reconciled implementation, and honestly-reported benchmark result makes it a little more trustworthy.
