"""
scoring.py — Aggregates rule costs into a single scalar score.

Separating this from rules.py means:
- Rules stay pure (just compute their own cost)
- Scoring logic (normalisation, future discounting, etc.) lives here
- Neither needs to know about the other's internals
"""

from __future__ import annotations
from typing import List, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import WorldState, Bus, BusResult, Weights, Route, Physics


def compute_score(
    world_state: "WorldState",
    bus: "Bus",
    result: "BusResult",
    weights: "Weights",
    committed_results: List["BusResult"],
    route: "Route",
    physics: "Physics",
    soft_rules: List[Any],
    hard_rules: List[Any],
) -> float:
    """
    Compute the total cost for a candidate BusResult.

    Steps:
      1. Run all hard rules — raises ValueError immediately on violation.
      2. Sum all soft rule costs — lower total = better plan.

    Returns a float score. The scheduler picks the plan with the lowest score.
    """
    context = dict(
        world_state=world_state,
        bus=bus,
        result=result,
        weights=weights,
        committed_results=committed_results,
        route=route,
        physics=physics,
    )

    # Hard rules first — any violation disqualifies this plan entirely
    for rule_fn in hard_rules:
        rule_fn(**context)   # raises ValueError on violation

    # Soft rules — sum weighted costs
    total = 0.0
    for rule_fn in soft_rules:
        total += rule_fn(**context)

    return total


def score_summary(results: List["BusResult"]) -> dict:
    """
    Compute aggregate stats over all committed results.
    Used by the UI for the metrics banner.
    """
    if not results:
        return {}

    waits = [r.total_wait_min for r in results]
    durations = [r.trip_duration_min for r in results]

    # Per-operator breakdown
    ops: dict = {}
    for r in results:
        op = r.bus.operator
        if op not in ops:
            ops[op] = {"waits": [], "durations": []}
        ops[op]["waits"].append(r.total_wait_min)
        ops[op]["durations"].append(r.trip_duration_min)

    op_summary = {}
    for op, data in ops.items():
        w = data["waits"]
        d = data["durations"]
        op_summary[op] = {
            "count": len(w),
            "avg_wait": sum(w) / len(w),
            "max_wait": max(w),
            "avg_duration": sum(d) / len(d),
        }

    return {
        "total_buses": len(results),
        "total_wait_min": sum(waits),
        "avg_wait_min": sum(waits) / len(waits),
        "max_wait_min": max(waits),
        "avg_duration_min": sum(durations) / len(durations),
        "operators": op_summary,
    }