"""Aggregate content-free measured latency samples; never benchmark mocks as real."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LatencySample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    real_services: bool
    stages_ms: dict[Literal["vad", "stt", "llm_ttfb", "tts_ttfb", "avatar", "transport", "total"], float]

    @field_validator("stages_ms")
    @classmethod
    def valid_stages(cls, values):
        import math
        if "total" not in values or any(not math.isfinite(value) or value < 0 for value in values.values()):
            raise ValueError("finite nonnegative total and stage timings required")
        return values


def percentile(values: list[float], fraction: float) -> float:
    if not values or not 0 <= fraction <= 1:
        raise ValueError("nonempty values and fraction in [0,1] required")
    values = sorted(values)
    position = (len(values) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def summarize_latency(samples: list[LatencySample], *, minimum_samples: int = 30) -> dict:
    if not samples or minimum_samples < 1:
        raise ValueError("samples and positive minimum required")
    stages = {}
    for stage in sorted({stage for sample in samples for stage in sample.stages_ms}):
        values = [sample.stages_ms[stage] for sample in samples if stage in sample.stages_ms]
        stages[stage] = {"count": len(values), "p50_ms": percentile(values, .5), "p95_ms": percentile(values, .95), "mean_ms": mean(values)}
    valid = all(sample.real_services for sample in samples) and len(samples) >= minimum_samples
    return {"samples": len(samples), "real_services": all(sample.real_services for sample in samples), "stages": stages,
            "target": {"p50_total_ms_lt": 1200, "status": ("passed" if stages["total"]["p50_ms"] < 1200 else "failed") if valid else "not_evaluated",
                       "reason": None if valid else "Requires real service measurements and minimum sample count"},
            "note": "total is measured end-of-candidate-speech to first avatar/audio output, not sum of stage percentiles"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSONL with real_services and stages_ms; no transcript/audio fields")
    parser.add_argument("--minimum-samples", type=int, default=30)
    args = parser.parse_args()
    samples = [LatencySample.model_validate_json(line) for line in args.input.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    result = summarize_latency(samples, minimum_samples=args.minimum_samples)
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result["target"]["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
