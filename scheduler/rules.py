"""
rules.py — Hard and soft scheduling rules.

Every rule is a pure function:
    (world_state, bus, result, weights, **context) -> float (cost)

Hard rules raise ValueError on violation.
Soft rules return a non-negative float cost — lower is better.

To add a new rule:
    1. Define the function here.
    2. Append it to SOFT_RULES (or HARD_RULES) in engine.py.
    That's it. No other changes needed.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import WorldState, Bus, BusResult, Weights


# Hard rules — raise on violation

def hard_range_constraint(
    world_state: "WorldState",
    bus: "Bus",
    result: "BusResult",
    weights: "Weights",
    route=None,
    physics=None,
    **_,
) -> float:
    """A bus must never travel more than battery_range_km between charges."""
    from .engine import build_cumulative_distances, _ordered_stops

    cum = build_cumulative_distances(route, bus.direction)
    stops = _ordered_stops(route, bus.direction)
    origin, dest = stops[0], stops[-1]
    checkpoints = [origin] + [cs.station_id for cs in result.charging_stops] + [dest]

    for i in range(len(checkpoints) - 1):
        gap = abs(cum[checkpoints[i + 1]] - cum[checkpoints[i]])
        if gap > physics.battery_range_km + 0.01:
            raise ValueError(
                f"{bus.id}: gap {checkpoints[i]}→{checkpoints[i+1]} "
                f"= {gap:.1f} km exceeds range {physics.battery_range_km} km"
            )
    return 0.0


def hard_station_order(
    world_state: "WorldState",
    bus: "Bus",
    result: "BusResult",
    weights: "Weights",
    route=None,
    **_,
) -> float:
    """Buses must visit stations in route order — no backtracking."""
    from .engine import charging_stations_in_order

    ordered = charging_stations_in_order(route, bus.direction)
    visited = [cs.station_id for cs in result.charging_stops]
    order_map = {sid: i for i, sid in enumerate(ordered)}
    indices = [order_map[v] for v in visited]
    if indices != sorted(indices):
        raise ValueError(f"{bus.id}: stations visited out of order: {visited}")
    return 0.0


# Soft rules — return cost float

def soft_individual_wait(
    world_state: "WorldState",
    bus: "Bus",
    result: "BusResult",
    weights: "Weights",
    **_,
) -> float:
    """Penalise per-bus total queue wait time."""
    return weights.individual * result.total_wait_min


def soft_operator_fairness(
    world_state: "WorldState",
    bus: "Bus",
    result: "BusResult",
    weights: "Weights",
    committed_results: List["BusResult"] = None,
    **_,
) -> float:
    """
    Penalise plans that push this bus's wait above its operator's current average.
    Encourages balanced treatment across an operator's fleet.
    """
    if not committed_results:
        return 0.0
    same_op = [r for r in committed_results if r.bus.operator == bus.operator]
    if not same_op:
        return 0.0
    avg_op_wait = sum(r.total_wait_min for r in same_op) / len(same_op)
    penalty = max(0.0, result.total_wait_min - avg_op_wait)
    return weights.operator * penalty


def soft_overall_throughput(
    world_state: "WorldState",
    bus: "Bus",
    result: "BusResult",
    weights: "Weights",
    **_,
) -> float:
    """
    Penalise excess trip time beyond the minimum possible (pure travel + charge time).
    Keeps total network throughput high.
    """
    excess = result.total_wait_min   # wait is the only source of excess time
    return weights.overall * excess


# Rule registries — edit here to add/remove rules

HARD_RULES = [
    hard_range_constraint,
    hard_station_order,
]

SOFT_RULES = [
    soft_individual_wait,
    soft_operator_fairness,
    soft_overall_throughput,
]