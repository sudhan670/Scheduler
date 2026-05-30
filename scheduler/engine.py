"""
engine.py — Core scheduling engine.

Responsibilities:
  - Parse scenario JSON into typed models
  - Enumerate all valid charging plans per bus
  - Simulate a bus through a plan against current world state
  - Greedy best-first scheduling loop
  - Route geometry helpers

The engine is intentionally rule-agnostic — it imports rules and scoring
but never hard-codes any cost logic. All optimisation lives in rules.py
and scoring.py.
"""

from __future__ import annotations
import json
import os
from typing import List, Dict, Tuple, Optional

from .models import (
    Segment, Station, Physics, Route, Bus, Weights,
    ChargingStop, BusResult, WorldState,
)
from .rules import HARD_RULES, SOFT_RULES
from .scoring import compute_score


def _ordered_stops(route: Route, direction: str) -> List[str]:
    """All stops in travel order including endpoints."""
    bk = [route.endpoints[0]] + [s.id for s in route.stations] + [route.endpoints[1]]
    return bk if direction == "BK" else list(reversed(bk))


def build_cumulative_distances(route: Route, direction: str) -> Dict[str, float]:
    """Cumulative km from origin for each stop."""
    stops = _ordered_stops(route, direction)
    segs = route.segments if direction == "BK" else list(reversed(route.segments))
    cum: Dict[str, float] = {stops[0]: 0.0}
    dist = 0.0
    for i, seg in enumerate(segs):
        dist += seg.distance_km
        cum[stops[i + 1]] = dist
    return cum


def charging_stations_in_order(route: Route, direction: str) -> List[str]:
    """Charging station IDs in travel order for this direction."""
    ids = [s.id for s in route.stations]
    return ids if direction == "BK" else list(reversed(ids))

def enumerate_valid_plans(route: Route, direction: str, physics: Physics) -> List[List[str]]:
    """
    Return all valid charging station subsets (ordered) such that no gap
    between consecutive checkpoints exceeds battery_range_km.

    Uses bitmask enumeration over 2^N station subsets (N=4 here = 16 combos).
    For larger N, replace with DP scan — the interface stays identical.
    """
    stations = charging_stations_in_order(route, direction)
    cum = build_cumulative_distances(route, direction)
    stops = _ordered_stops(route, direction)
    origin, dest = stops[0], stops[-1]

    valid = []
    n = len(stations)
    for mask in range(1 << n):
        chosen = [stations[i]  for i in range(n) if (mask >> i) & 1]
        checkpoints = [origin] + chosen + [dest]
        feasible = all(
            abs(cum[checkpoints[j + 1]] - cum[checkpoints[j]]) <= physics.battery_range_km
            for j in range(len(checkpoints) - 1)
        )
        if feasible:
            valid.append(chosen)
    return valid

def simulate_bus(bus: Bus, plan: List[str], route: Route, physics: Physics, world_state: WorldState,
) -> Tuple[BusResult, WorldState]:
    """
    Simulate bus through a charging plan against a copy of world_state.
    Returns (BusResult, updated WorldState copy). Original ws is untouched.
    """
    ws = world_state.copy() # to take copy of the world_state
    cum = build_cumulative_distances(route, bus.direction)
    stops = _ordered_stops(route, bus.direction)
    dest = stops[-1]

    current_time = bus.departure_min
    current_stop = stops[0]
    charging_stops: List[ChargingStop] = []

    for station_id in plan:
        dist = abs(cum[station_id] - cum[current_stop])
        travel_min = (dist / physics.speed_kmh) * 60.0
        arrive = current_time + travel_min

        station = next(s for s in route.stations if s.id == station_id)
        wait_min, charge_start = ws.earliest_slot(
            station_id, arrive, physics.charge_time_min, station.chargers
        )
        charge_end = charge_start + physics.charge_time_min

        ws.book_slot(station_id, charge_start, charge_end)
        charging_stops.append(ChargingStop(
            station_id=station_id,
            arrive_min=arrive,
            queue_wait_min=wait_min,
            charge_start_min=charge_start,
            charge_end_min=charge_end,
        ))
        current_time = charge_end
        current_stop = station_id

    dist_to_dest = abs(cum[dest] - cum[current_stop])
    arrival_min = current_time + (dist_to_dest / physics.speed_kmh) * 60.0

    result = BusResult(
        bus=bus,
        charging_stops=charging_stops,
        departure_min=bus.departure_min,
        arrival_min=arrival_min,
    )
    return result, ws

# Main scheduler loop

def schedule(scenario: Dict) -> List[BusResult]:
    """
    Main entry point. Parses a scenario dict and returns a list of BusResult.

    Algorithm: greedy best-first.
      For each bus (sorted by departure time):
        1. Enumerate all valid charging plans.
        2. Simulate each plan against current world state.
        3. Score each simulation using rules + weights.
        4. Commit the lowest-cost plan.
    """
    route   = _parse_route(scenario)
    physics = _parse_physics(scenario)
    weights = _parse_weights(scenario)
    buses   = sorted(_parse_buses(scenario), key=lambda b: b.departure_min)

    world_state = WorldState(
        station_schedule={s.id: [] for s in route.stations}
    )
    committed: List[BusResult] = []

    for bus in buses:
        plans = enumerate_valid_plans(route, bus.direction, physics)

        best_result: Optional[BusResult] = None
        best_ws: Optional[WorldState]    = None
        best_score = float("inf")

        for plan in plans:
            try:
                result, new_ws = simulate_bus(bus, plan, route, physics, world_state)
                score = compute_score(
                    world_state=new_ws,
                    bus=bus,
                    result=result,
                    weights=weights,
                    committed_results=committed,
                    route=route,
                    physics=physics,
                    soft_rules=SOFT_RULES,
                    hard_rules=HARD_RULES,
                )
            except ValueError:
                continue   # hard rule violation — skip this plan

            if score < best_score:
                best_score  = score
                best_result = result
                best_ws     = new_ws

        if best_result is None:
            raise RuntimeError(f"No valid plan found for {bus.id}")

        world_state = best_ws
        committed.append(best_result)

    return committed

# Scenario parsers

def _parse_route(scenario: Dict) -> Route:
    r = scenario["route"]
    stations = [Station(s["id"], s["name"], s.get("chargers", 1)) for s in r["stations"]]
    segments = [Segment(s["from"], s["to"], s["distance_km"]) for s in r["segments"]]
    return Route(
        id=r["id"], name=r["name"],
        endpoints=r["endpoints"],
        stations=stations,
        segments=segments,
    )


def _parse_physics(scenario: Dict) -> Physics:
    p = scenario["physics"]
    return Physics(
        battery_range_km=p["battery_range_km"],
        charge_time_min=p["charge_time_min"],
        speed_kmh=p["speed_kmh"],
    )


def _parse_weights(scenario: Dict) -> Weights:
    w = scenario.get("weights", {})
    known = {"individual", "operator", "overall"}
    return Weights(
        individual=w.get("individual", 1.0),
        operator=w.get("operator", 1.0),
        overall=w.get("overall", 1.0),
        extra={k: v for k, v in w.items() if k not in known},
    )


def _parse_buses(scenario: Dict) -> List[Bus]:
    buses = []
    for b in scenario["buses"]:
        h, m = map(int, b["departure"].split(":"))
        buses.append(Bus(
            id=b["id"],
            operator=b["operator"],
            direction=b["direction"],
            departure_min=float(h * 60 + m),
        ))
    return buses

# Utilities

def min_to_hhmm(minutes: float) -> str:
    h = int(minutes) // 60
    m = int(minutes) % 60
    return f"{h:02d}:{m:02d}"


def load_scenario_files(scenarios_dir: str) -> Dict[str, Dict]:
    """Load all scenario JSON files, keyed by scenario id."""
    result = {}
    for fname in sorted(os.listdir(scenarios_dir)):
        if fname.endswith(".json"):
            with open(os.path.join(scenarios_dir, fname)) as f:
                data = json.load(f)
            result[data["id"]] = data
    return result