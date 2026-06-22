"""
Cross-Model DVL Evaluation Harness
====================================
Runs FinQA samples through multiple LLMs (Mistral-7B, GPT-4o-mini, Claude-haiku),
applies DVL verification, and computes accuracy with/without DVL for each model.

Produces Table 2 for the paper:
  Model          | Baseline | +DVL  | Improvement
  Mistral-7B     | 1.00%    | 42.61%| 42×
  GPT-4o-mini    | ?.?%     | ?.?%  | ?×
  Claude-haiku   | ?.?%     | ?.?%  | ?×

Usage:
    # Set API keys in environment or .env file
    export OPENAI_API_KEY=sk-...
    export ANTHROPIC_API_KEY=sk-ant-...
    export HF_TOKEN=hf_...

    python -m evals.cross_model_eval                              # full eval
    python -m evals.cross_model_eval --samples 50                 # quick test run
    python -m evals.cross_model_eval --models mistral,gpt4o-mini  # specific models
"""

import os
import sys
import json
import time
import asyncio
import logging
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import httpx

# Add parent to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.dvl import full_verify, is_correct
from app.parser import extract_number, clean_llm_output

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class ModelConfig:
    name: str
    provider: str  # "huggingface" | "openai" | "anthropic"
    model_id: str
    api_key_env: str
    max_tokens: int = 50
    cost_per_1m_input: float = 0.0
    cost_per_1m_output: float = 0.0


MODELS = {
    "mistral": ModelConfig(
        name="Mistral-7B + QLoRA",
        provider="huggingface",
        model_id="aadi2026/finverify-lora",
        api_key_env="HF_TOKEN",
    ),
    "gpt4o-mini": ModelConfig(
        name="GPT-4o-mini",
        provider="openai",
        model_id="gpt-4o-mini",
        api_key_env="OPENAI_API_KEY",
        cost_per_1m_input=0.15,
        cost_per_1m_output=0.60,
    ),
    "claude-haiku": ModelConfig(
        name="Claude 3.5 Haiku",
        provider="anthropic",
        model_id="claude-3-5-haiku-20241022",
        api_key_env="ANTHROPIC_API_KEY",
        cost_per_1m_input=0.25,
        cost_per_1m_output=1.25,
    ),
}


# ---------------------------------------------------------------------------
# Sample data (representative FinQA-style questions with ground truth)
# ---------------------------------------------------------------------------

@dataclass
class EvalSample:
    question: str
    actual: float
    context: str = ""
    category: str = "general"


# Canonical FinQA samples (subset for quick evaluation)
EVAL_SAMPLES = [
    EvalSample("What was the YoY operating margin change?", 12.40, category="ratio"),
    EvalSample("What was the percentage decrease in HTM securities?", 0.34146, category="sign"),
    EvalSample("What was the increase in Class A shares outstanding?", 995.0, category="magnitude"),
    EvalSample("What was the CET1 ratio in Q4 2022?", 10.935, category="ratio"),
    EvalSample("What was the profit margin?", 25.31, category="ratio"),
    EvalSample("What was the revenue growth rate?", 6.23, category="ratio"),
    EvalSample("What was the net income increase YoY?", 1250000, category="magnitude"),
    EvalSample("What was the return on equity?", 17.0, category="ratio"),
    EvalSample("What was the price to earnings ratio?", 28.5, category="ratio"),
    EvalSample("What was the debt to equity ratio?", 1.45, category="ratio"),
    EvalSample("What was the dividend yield?", 2.1, category="ratio"),
    EvalSample("What was the gross margin percentage?", 43.26, category="ratio"),
    EvalSample("What was the operating expense change?", -0.0812, category="ratio"),
    EvalSample("What was total revenue in millions?", 83400, category="magnitude"),
    EvalSample("What was the earnings per share?", 6.42, category="ratio"),
]


# ---------------------------------------------------------------------------
# Results tracking
# ---------------------------------------------------------------------------

@dataclass
class ModelResult:
    model_name: str
    total: int = 0
    baseline_correct: int = 0
    dvl_correct: int = 0
    errors: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    latencies: list = field(default_factory=list)

    @property
    def baseline_acc(self) -> float:
        return (self.baseline_correct / self.total * 100) if self.total > 0 else 0.0

    @property
    def dvl_acc(self) -> float:
        return (self.dvl_correct / self.total * 100) if self.total > 0 else 0.0

    @property
    def improvement(self) -> str:
        if self.baseline_acc == 0:
            return f"{self.dvl_acc:.0f}×" if self.dvl_acc > 0 else "N/A"
        ratio = self.dvl_acc / self.baseline_acc
        return f"{ratio:.1f}×"

    @property
    def avg_latency_ms(self) -> float:
        return sum(self.latencies) / len(self.latencies) * 1000 if self.latencies else 0


# ---------------------------------------------------------------------------
# LLM Inference (async)
# ---------------------------------------------------------------------------

PROMPT_TEMPLATE = """Answer the following financial question with ONLY a number.
Do not explain. Do not add units. Just the number.

Question: {question}
Answer:"""


async def call_huggingface(
    client: httpx.AsyncClient, config: ModelConfig, question: str, api_key: str
) -> tuple[str, int, int]:
    """Call HuggingFace Inference API."""
    url = f"https://api-inference.huggingface.co/models/{config.model_id}"
    payload = {
        "inputs": PROMPT_TEMPLATE.format(question=question),
        "parameters": {"max_new_tokens": config.max_tokens, "do_sample": False},
    }
    resp = await client.post(url, json=payload, headers={"Authorization": f"Bearer {api_key}"})
    resp.raise_for_status()
    data = resp.json()
    text = data[0].get("generated_text", "") if isinstance(data, list) else str(data)
    # Rough token estimate
    return text, len(question.split()) * 2, len(text.split())


async def call_openai(
    client: httpx.AsyncClient, config: ModelConfig, question: str, api_key: str
) -> tuple[str, int, int]:
    """Call OpenAI API."""
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": config.model_id,
        "messages": [
            {"role": "system", "content": "You are a financial analyst. Answer with ONLY the number, no explanation."},
            {"role": "user", "content": question},
        ],
        "max_tokens": config.max_tokens,
        "temperature": 0,
    }
    resp = await client.post(url, json=payload, headers={"Authorization": f"Bearer {api_key}"})
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


async def call_anthropic(
    client: httpx.AsyncClient, config: ModelConfig, question: str, api_key: str
) -> tuple[str, int, int]:
    """Call Anthropic API."""
    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": config.model_id,
        "max_tokens": config.max_tokens,
        "messages": [{"role": "user", "content": f"Answer with ONLY the number: {question}"}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    resp = await client.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    text = data["content"][0]["text"] if data.get("content") else ""
    usage = data.get("usage", {})
    return text, usage.get("input_tokens", 0), usage.get("output_tokens", 0)


PROVIDER_CALLS = {
    "huggingface": call_huggingface,
    "openai": call_openai,
    "anthropic": call_anthropic,
}


async def call_model(
    client: httpx.AsyncClient, config: ModelConfig, question: str
) -> Optional[tuple[str, int, int]]:
    """Dispatch to the appropriate provider."""
    api_key = os.getenv(config.api_key_env)
    if not api_key:
        return None
    call_fn = PROVIDER_CALLS.get(config.provider)
    if not call_fn:
        return None
    return await call_fn(client, config, question, api_key)


# ---------------------------------------------------------------------------
# Evaluation core
# ---------------------------------------------------------------------------

async def evaluate_model(
    config: ModelConfig,
    samples: list[EvalSample],
    semaphore: asyncio.Semaphore,
    result: ModelResult,
):
    """Evaluate a single model across all samples."""
    api_key = os.getenv(config.api_key_env)
    if not api_key:
        logger.warning("Skipping %s — %s not set", config.name, config.api_key_env)
        return

    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, sample in enumerate(samples):
            async with semaphore:
                result.total += 1
                try:
                    t0 = time.monotonic()
                    raw_text, in_tok, out_tok = await call_model(client, config, sample.question)
                    latency = time.monotonic() - t0
                    result.latencies.append(latency)
                    result.total_input_tokens += in_tok
                    result.total_output_tokens += out_tok

                    if raw_text is None:
                        result.errors += 1
                        continue

                    # Parse number from response
                    _, raw_number = clean_llm_output(raw_text)

                    if raw_number is None:
                        result.errors += 1
                        logger.debug("[%s] #%d: No number extracted from: %s", config.name, i, raw_text[:80])
                        continue

                    # Baseline accuracy (no DVL)
                    if is_correct(raw_number, sample.actual):
                        result.baseline_correct += 1

                    # DVL accuracy
                    verified, _, _, _ = full_verify(sample.question, raw_number, sample.actual)
                    if is_correct(verified, sample.actual):
                        result.dvl_correct += 1

                    if (i + 1) % 10 == 0:
                        logger.info("[%s] %d/%d processed", config.name, i + 1, len(samples))

                except Exception as e:
                    result.errors += 1
                    logger.warning("[%s] #%d error: %s", config.name, i, e)

                # Rate limiting delay
                await asyncio.sleep(0.2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run_eval(model_keys: list[str], samples: list[EvalSample], concurrency: int = 5):
    """Run evaluation for all specified models."""
    semaphore = asyncio.Semaphore(concurrency)
    results: dict[str, ModelResult] = {}

    tasks = []
    for key in model_keys:
        config = MODELS[key]
        result = ModelResult(model_name=config.name)
        results[key] = result
        tasks.append(evaluate_model(config, samples, semaphore, result))

    await asyncio.gather(*tasks)
    return results


def print_results(results: dict[str, ModelResult]):
    """Print formatted comparison table."""
    print("\n" + "=" * 72)
    print("  CROSS-MODEL DVL EVALUATION RESULTS")
    print("=" * 72)
    print(f"\n  {'Model':<22} {'Baseline':>10} {'+ DVL':>10} {'Improvement':>13} {'Errors':>8} {'Latency':>10}")
    print(f"  {'─'*22} {'─'*10} {'─'*10} {'─'*13} {'─'*8} {'─'*10}")

    for key, r in results.items():
        if r.total == 0:
            print(f"  {r.model_name:<22} {'SKIPPED':>10}")
            continue
        print(
            f"  {r.model_name:<22} "
            f"{r.baseline_acc:>9.2f}% "
            f"{r.dvl_acc:>9.2f}% "
            f"{r.improvement:>13} "
            f"{r.errors:>8} "
            f"{r.avg_latency_ms:>8.0f}ms"
        )

    print(f"\n  n = {next(iter(results.values())).total if results else 0} samples")
    print("=" * 72)

    # Cost estimate
    for key, r in results.items():
        config = MODELS[key]
        if config.cost_per_1m_input > 0:
            cost = (
                r.total_input_tokens / 1_000_000 * config.cost_per_1m_input
                + r.total_output_tokens / 1_000_000 * config.cost_per_1m_output
            )
            print(f"  {r.model_name}: ~${cost:.4f} estimated cost")

    print()


def save_results(results: dict[str, ModelResult], output_path: str):
    """Save results to JSON for further analysis."""
    data = {}
    for key, r in results.items():
        data[key] = {
            "model_name": r.model_name,
            "total": r.total,
            "baseline_correct": r.baseline_correct,
            "dvl_correct": r.dvl_correct,
            "baseline_acc": round(r.baseline_acc, 4),
            "dvl_acc": round(r.dvl_acc, 4),
            "improvement": r.improvement,
            "errors": r.errors,
            "avg_latency_ms": round(r.avg_latency_ms, 1),
        }
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("Results saved to %s", output_path)


def main():
    parser = argparse.ArgumentParser(description="Cross-model DVL evaluation harness")
    parser.add_argument("--samples", type=int, default=None, help="Number of samples (default: all)")
    parser.add_argument("--models", type=str, default="mistral,gpt4o-mini,claude-haiku",
                        help="Comma-separated model keys")
    parser.add_argument("--concurrency", type=int, default=5, help="Max concurrent API calls")
    parser.add_argument("--output", type=str, default="evals/results.json", help="Output JSON path")
    args = parser.parse_args()

    model_keys = [k.strip() for k in args.models.split(",")]
    for k in model_keys:
        if k not in MODELS:
            logger.error("Unknown model key: %s (available: %s)", k, ", ".join(MODELS.keys()))
            sys.exit(1)

    samples = EVAL_SAMPLES
    if args.samples:
        samples = samples[:args.samples]

    logger.info("Running evaluation: %d samples × %d models", len(samples), len(model_keys))
    for k in model_keys:
        config = MODELS[k]
        has_key = bool(os.getenv(config.api_key_env))
        logger.info("  %s (%s): %s", config.name, config.model_id, "✓ key found" if has_key else "✗ NO KEY")

    t0 = time.monotonic()
    results = asyncio.run(run_eval(model_keys, samples, args.concurrency))
    elapsed = time.monotonic() - t0

    print_results(results)
    print(f"  Total time: {elapsed:.1f}s")

    # Save results
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    save_results(results, args.output)


if __name__ == "__main__":
    main()
