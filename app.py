"""
app.py — Streamlit UI for Electric Bus Charging Scheduler
"""

import streamlit as st
import pandas as pd

from scheduler import (schedule, load_scenario_files, min_to_hhmm, score_summary,)
from scheduler.models import BusResult


st.set_page_config(page_title="Electric Bus Charging Scheduler",page_icon="🚌",layout="wide",)
st.title("🚌 Electric Bus Charging Scheduler")
SCENARIO_DIR = "scenarios"

try:
    scenarios = load_scenario_files(SCENARIO_DIR)
except Exception as e:
    st.error(f"Failed to load scenarios: {e}")
    st.stop()

if not scenarios:
    st.warning("No scenario files found.")
    st.stop()

scenario_ids = list(scenarios.keys())
selected_id = st.sidebar.selectbox("Select Scenario",scenario_ids,)
scenario = scenarios[selected_id]
st.sidebar.success(f"Loaded: {selected_id}")

if st.button("Run Scheduler", type="primary",):
    try:
        results = schedule(scenario)
    except Exception as e:
        st.exception(e)
        st.stop()
    st.success(f"Successfully scheduled {len(results)} buses")
    st.subheader("Summary")

    try:
        summary = score_summary(results)
        if isinstance(summary, dict):
            for key, value in summary.items():
                st.metric(key, value)
        else:
            st.write(summary)

    except Exception as e:
        st.warning(f"Could not generate score summary: {e}")

    st.subheader("Bus Schedules")

    rows = []
    for result in results:
        plan = " → ".join(stop.station_id
            for stop in result.charging_stops
        )

        rows.append(
            {
                "Bus": result.bus.id,
                "Operator": result.bus.operator,
                "Direction": result.bus.direction,
                "Departure": min_to_hhmm(result.departure_min),
                "Arrival": min_to_hhmm(result.arrival_min),
                "Charging Stops": plan if plan else "None",
                "Charges": len(result.charging_stops),
            }
        )

    st.dataframe(pd.DataFrame(rows),use_container_width=True,)
    st.subheader("Charging Events")
    charge_rows = []

    for result in results:
        for stop in result.charging_stops:
            charge_rows.append(
                {
                    "Bus": result.bus.id,
                    "Station": stop.station_id,
                    "Arrival": min_to_hhmm(stop.arrive_min),
                    "Queue Wait (min)": round(stop.queue_wait_min, 1),
                    "Charge Start": min_to_hhmm(stop.charge_start_min),
                    "Charge End": min_to_hhmm(stop.charge_end_min),
                }
            )

    if charge_rows:
        st.dataframe(
            pd.DataFrame(charge_rows),
            use_container_width=True,
        )
    else:
        st.info("No charging events required.")

    st.subheader("Bus Details")

    for result in results:
        with st.expander(f"Bus {result.bus.id}"):
            st.write(f"Operator: {result.bus.operator}")
            st.write(f"Direction: {result.bus.direction}")
            st.write(
                f"Departure: {min_to_hhmm(result.departure_min)}"
            )
            st.write(
                f"Arrival: {min_to_hhmm(result.arrival_min)}"
            )

            if result.charging_stops:
                details = []
                for stop in result.charging_stops:
                    details.append(
                        {
                            "Station": stop.station_id,
                            "Arrive": min_to_hhmm(stop.arrive_min),
                            "Wait": round(stop.queue_wait_min, 1),
                            "Charge Start": min_to_hhmm(
                                stop.charge_start_min
                            ),
                            "Charge End": min_to_hhmm(
                                stop.charge_end_min
                            ),
                        }
                    )
                st.dataframe(
                    pd.DataFrame(details),
                    use_container_width=True,
                )

            else:
                st.info("No charging stops required.")


    csv = pd.DataFrame(rows).to_csv(index=False)

    st.download_button(label="Download Schedule CSV", data=csv, file_name=f"{selected_id}_schedule.csv",mime="text/csv",)