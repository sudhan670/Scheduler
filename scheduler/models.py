"""
models.py — All dataclasses used across the scheduler.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

# Here I use Generic Models to include standrad version that helps me to understand the code work better 
# and generic methods to done the all predefined works so it is easy to work on it
# I setted all predefined works here it is easy for me to go ahead the work progress

@dataclass
class Segment:
    from_stop: str
    to_stop: str
    distance_km: float

    def travel_time_min(self, speed_kmh: float) -> float:
        return (self.distance_km / speed_kmh) * 60.0


@dataclass
class Station:
    id: str
    name: str
    chargers: int = 1  # extensible: multiple chargers per station


@dataclass
class Physics:
    battery_range_km: float
    charge_time_min: float
    speed_kmh: float


@dataclass
class Route:
    id: str
    name: str
    endpoints: List[str]       # [origin, destination]
    stations: List[Station]    # in BK order
    segments: List[Segment]    # all segments in BK order


@dataclass
class Bus:
    id: str
    operator: str
    direction: str             # "BK" or "KB"
    departure_min: float       # minutes from midnight


@dataclass
class Weights:
    individual: float = 1.0
    operator: float = 1.0
    overall: float = 1.0
    # Extra named weights for future rules — no model changes needed
    extra: Dict[str, float] = field(default_factory=dict)


@dataclass
class ChargingStop:
    station_id: str
    arrive_min: float
    queue_wait_min: float
    charge_start_min: float
    charge_end_min: float


@dataclass
class BusResult:
    bus: Bus
    charging_stops: List[ChargingStop]
    departure_min: float
    arrival_min: float

    @property
    def total_wait_min(self) -> float:
        return sum(s.queue_wait_min for s in self.charging_stops)

    @property
    def trip_duration_min(self) -> float:
        return self.arrival_min - self.departure_min


@dataclass
class WorldState:
    """
    Tracks charger bookings at each station.
    station_schedule: station_id -> list of (charge_start, charge_end) slots
    """
    station_schedule: Dict[str, List[Tuple[float, float]]]

    def copy(self) -> "WorldState":
        return WorldState(
            station_schedule={k: list(v) for k, v in self.station_schedule.items()}
        )

    def earliest_slot(self,station_id: str, arrive_min: float,charge_time_min: float, num_chargers: int,) -> Tuple[float, float]:
        """
        Returns (wait_min, charge_start_min) — the earliest available charger slot
        at or after arrive_min. Respects num_chargers for parallel booking.
        """
        slots = self.station_schedule[station_id]
        start = arrive_min
        changed = True
        while changed:
            changed = False
            # Count how many bookings overlap [start, start+charge_time]
            overlapping = [
                (s, e) for (s, e) in slots
                if start < e and (start + charge_time_min) > s
            ]
            if len(overlapping) >= num_chargers:
                # Push past the earliest-ending overlap
                start = min(e for (_, e) in overlapping)
                changed = True
        return start - arrive_min, start

    def book_slot(self, station_id: str, charge_start: float, charge_end: float):
        self.station_schedule[station_id].append((charge_start, charge_end))
        self.station_schedule[station_id].sort(key=lambda x: x[0])