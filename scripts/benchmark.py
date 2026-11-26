from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def request_once(url: str, timeout: float) -> tuple[float, int | None, str | None]:
    started = time.perf_counter()
    try:
        with urlopen(url, timeout=timeout) as response:
            response.read()
            return (time.perf_counter() - started) * 1000, response.status, None
    except HTTPError as error:
        return (time.perf_counter() - started) * 1000, error.code, str(error)
    except (URLError, TimeoutError, OSError) as error:
        return (time.perf_counter() - started) * 1000, None, str(error)


def percentile(values: list[float], quantile: float) -> float:
    index = max(0, math.ceil(quantile * len(values)) - 1)
    return sorted(values)[index]


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure local HTTP endpoint response time.")
    parser.add_argument("--url", default="http://127.0.0.1:8000/health")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1 or args.timeout <= 0:
        parser.error("Request count, concurrency, and timeout must be positive.")

    warmup = [request_once(args.url, args.timeout) for _ in range(min(5, args.requests))]
    if any(status is None or status >= 400 for _, status, _ in warmup):
        print(json.dumps({"error": "Warm-up request failed", "details": warmup}))
        return 1

    started = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [executor.submit(request_once, args.url, args.timeout) for _ in range(args.requests)]
        for future in as_completed(futures):
            results.append(future.result())
    elapsed = time.perf_counter() - started

    latencies = [latency for latency, _, _ in results]
    successes = sum(status is not None and 200 <= status < 300 for _, status, _ in results)
    failures = [error or f"HTTP {status}" for _, status, error in results if status is None or status >= 400]
    summary = {
        "url": args.url,
        "warmup_requests": len(warmup),
        "measured_requests": args.requests,
        "concurrency": args.concurrency,
        "successes": successes,
        "failures": len(failures),
        "elapsed_seconds": round(elapsed, 4),
        "requests_per_second": round(args.requests / elapsed, 2),
        "latency_ms": {
            "min": round(min(latencies), 3),
            "mean": round(statistics.fmean(latencies), 3),
            "median": round(statistics.median(latencies), 3),
            "p95": round(percentile(latencies, 0.95), 3),
            "max": round(max(latencies), 3),
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if successes == args.requests else 1


if __name__ == "__main__":
    raise SystemExit(main())
