#!/usr/bin/env python3
"""Async OpenAI-compatible LLM serving benchmark.

Measures:
- TTFT from streaming chunks
- total latency
- output token count approximation
- success/failure/timeout
- per-concurrency summary CSV
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import statistics
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import aiohttp

try:
    import tiktoken
except Exception:  # pragma: no cover
    tiktoken = None


@dataclass
class RequestResult:
    concurrency: int
    request_id: int
    prompt_id: str
    ok: bool
    status: int | None
    ttft_s: float | None
    latency_s: float
    input_tokens: int
    output_tokens: int
    tokens_per_s: float | None
    error: str | None


def load_prompts(path: Path) -> list[dict[str, Any]]:
    prompts = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            obj.setdefault("id", f"prompt-{i}")
            if "messages" not in obj:
                obj["messages"] = [{"role": "user", "content": obj["prompt"]}]
            prompts.append(obj)
    if not prompts:
        raise ValueError(f"no prompts in {path}")
    return prompts


def count_tokens(text: str) -> int:
    if not text:
        return 0
    if tiktoken is None:
        return max(1, len(text.split()))
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def messages_text(messages: list[dict[str, str]]) -> str:
    return "\n".join(m.get("content", "") for m in messages)


async def one_request(
    session: aiohttp.ClientSession,
    *,
    base_url: str,
    api_key: str | None,
    model: str,
    prompt: dict[str, Any],
    request_id: int,
    concurrency: int,
    max_tokens: int,
    temperature: float,
    timeout_s: float,
) -> RequestResult:
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "messages": prompt["messages"],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }
    if "extra" in prompt:
        payload.update(prompt["extra"])

    input_tokens = count_tokens(messages_text(prompt["messages"]))
    start = time.perf_counter()
    ttft = None
    output_text = []
    status = None
    error = None

    try:
        async with session.post(url, headers=headers, json=payload, timeout=timeout_s) as resp:
            status = resp.status
            if resp.status >= 400:
                body = await resp.text()
                raise RuntimeError(f"HTTP {resp.status}: {body[:500]}")
            async for raw in resp.content:
                now = time.perf_counter()
                line = raw.decode("utf-8", errors="ignore")
                for part in line.splitlines():
                    part = part.strip()
                    if not part.startswith("data:"):
                        continue
                    data = part[5:].strip()
                    if data == "[DONE]":
                        continue
                    if ttft is None:
                        ttft = now - start
                    try:
                        obj = json.loads(data)
                        delta = obj.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content") or ""
                        if content:
                            output_text.append(content)
                    except Exception:
                        pass
        latency = time.perf_counter() - start
        out = "".join(output_text)
        output_tokens = count_tokens(out)
        return RequestResult(
            concurrency=concurrency,
            request_id=request_id,
            prompt_id=str(prompt.get("id")),
            ok=True,
            status=status,
            ttft_s=ttft,
            latency_s=latency,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tokens_per_s=(output_tokens / latency) if latency > 0 else None,
            error=None,
        )
    except Exception as e:
        latency = time.perf_counter() - start
        error = repr(e)
        return RequestResult(
            concurrency=concurrency,
            request_id=request_id,
            prompt_id=str(prompt.get("id")),
            ok=False,
            status=status,
            ttft_s=ttft,
            latency_s=latency,
            input_tokens=input_tokens,
            output_tokens=0,
            tokens_per_s=None,
            error=error,
        )


async def run_concurrency(args: argparse.Namespace, prompts: list[dict[str, Any]], concurrency: int) -> list[RequestResult]:
    connector = aiohttp.TCPConnector(limit=max(concurrency * 2, 8))
    async with aiohttp.ClientSession(connector=connector) as session:
        sem = asyncio.Semaphore(concurrency)
        results: list[RequestResult] = []

        async def run_one(i: int):
            async with sem:
                prompt = prompts[i % len(prompts)]
                res = await one_request(
                    session,
                    base_url=args.base_url,
                    api_key=args.api_key,
                    model=args.model,
                    prompt=prompt,
                    request_id=i,
                    concurrency=concurrency,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                    timeout_s=args.timeout,
                )
                results.append(res)

        # warmup is intentionally not returned
        warmup_tasks = [run_one(-(i + 1)) for i in range(args.warmup)]
        await asyncio.gather(*warmup_tasks)
        results.clear()

        tasks = [run_one(i) for i in range(args.requests)]
        await asyncio.gather(*tasks)
        return sorted(results, key=lambda r: r.request_id)


def pct(values: list[float], p: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    idx = min(len(values) - 1, max(0, int(round((p / 100) * (len(values) - 1)))))
    return values[idx]


def summarize(results: list[RequestResult]) -> dict[str, Any]:
    ok = [r for r in results if r.ok]
    lat = [r.latency_s for r in ok]
    ttft = [r.ttft_s for r in ok if r.ttft_s is not None]
    total_out = sum(r.output_tokens for r in ok)
    total_time = max((r.latency_s for r in results), default=0.0)
    return {
        "concurrency": results[0].concurrency if results else None,
        "requests": len(results),
        "success": len(ok),
        "failures": len(results) - len(ok),
        "failure_rate": (len(results) - len(ok)) / len(results) if results else None,
        "latency_p50_s": pct(lat, 50),
        "latency_p90_s": pct(lat, 90),
        "latency_p95_s": pct(lat, 95),
        "latency_p99_s": pct(lat, 99),
        "ttft_p50_s": pct(ttft, 50),
        "ttft_p90_s": pct(ttft, 90),
        "ttft_p95_s": pct(ttft, 95),
        "output_tokens": total_out,
        "aggregate_output_tokens_per_s": total_out / total_time if total_time > 0 else None,
        "mean_request_tokens_per_s": statistics.mean([r.tokens_per_s for r in ok if r.tokens_per_s is not None]) if ok else None,
    }


async def amain(args: argparse.Namespace) -> None:
    prompts = load_prompts(Path(args.prompts))
    all_results: list[RequestResult] = []
    summaries: list[dict[str, Any]] = []
    for c in args.concurrency:
        print(f"running concurrency={c} requests={args.requests} warmup={args.warmup}", flush=True)
        results = await run_concurrency(args, prompts, c)
        all_results.extend(results)
        summaries.append(summarize(results))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")

    summary = Path(args.summary)
    summary.parent.mkdir(parents=True, exist_ok=True)
    with summary.open("w", newline="", encoding="utf-8") as f:
        fields = list(summaries[0].keys()) if summaries else []
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(summaries)

    print(f"raw: {out}")
    print(f"summary: {summary}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True, help="OpenAI-compatible base URL, e.g. http://host:8000/v1")
    p.add_argument("--api-key", default=None)
    p.add_argument("--model", required=True)
    p.add_argument("--prompts", required=True)
    p.add_argument("--concurrency", default="1", type=lambda s: [int(x) for x in s.split(",")])
    p.add_argument("--requests", type=int, default=100)
    p.add_argument("--warmup", type=int, default=10)
    p.add_argument("--max-tokens", type=int, default=128)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--timeout", type=float, default=120.0)
    p.add_argument("--out", default="results/bench.jsonl")
    p.add_argument("--summary", default="results/summary.csv")
    return p.parse_args()


def main() -> None:
    asyncio.run(amain(parse_args()))


if __name__ == "__main__":
    main()
