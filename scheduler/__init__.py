"""
scheduler/ — Electric bus charging scheduler package.

Public API (everything app.py needs):
    from scheduler import schedule, load_scenario_files, min_to_hhmm, score_summary
    from scheduler.models import BusResult, ChargingStop
"""

from .engine import schedule, load_scenario_files, min_to_hhmm
from .scoring import score_summary
from .models import BusResult, ChargingStop, Weights

__all__ = [
    "schedule",
    "load_scenario_files",
    "min_to_hhmm",
    "score_summary",
    "BusResult",
    "ChargingStop",
    "Weights",
]