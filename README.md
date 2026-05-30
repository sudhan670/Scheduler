# Electric Bus Charging Scheduler

A scalable charging scheduler for electric buses operating between Bengaluru and Kochi.

Built using:

* Python
* Streamlit
* Event-driven scheduling engine
* Rule-based optimization framework

---

## Problem Overview

Electric buses travel along a fixed route:

Bengaluru → A → B → C → D → Kochi

Each bus:

* Starts fully charged (240 km range)
* Charges to full in 25 minutes
* Must never travel more than 240 km without charging
* Shares charging infrastructure with other buses

Each charging station contains limited charger capacity (1 charger in the provided scenarios).

The scheduler decides:

1. Which charging stations each bus uses
2. When each bus charges
3. Which bus receives charger access when contention occurs

---

## Features

* Supports all 5 assignment scenarios
* Event-driven simulation engine
* Configurable optimization weights
* Extensible hard-rule validation
* Extensible soft-rule scoring
* Scenario-driven configuration
* Streamlit UI

---

## Project Structure

```text
project/
│
├── app.py
│
├── scheduler/
│   ├── engine.py
│   ├── scoring.py
│   ├── rules.py
│   ├── models.py
│   ├── validation.py
│   └── utils.py
│
├── scenarios/
│   ├── scenario_1.yaml
│   ├── scenario_2.yaml
│   ├── scenario_3.yaml
│   ├── scenario_4.yaml
│   └── scenario_5.yaml
│
├── README.md
├── ARCHITECTURE.md
└── requirements.txt
```

---

## Installation

```bash
git clone <repo-url>

cd bus-charging-scheduler

pip install -r requirements.txt
```

---

## Running Locally

```bash
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

---

## Scenario Configuration

All scenarios live inside:

```text
scenarios/
```

Each scenario contains:

* Route definition
* Stations
* Bus departures
* Weight configuration

Example:

```yaml
weights:
  individual: 1.0
  operator: 1.0
  overall: 1.0
```

---

## Changing Optimization Weights

Weights are loaded from scenario files.

Example:

```yaml
weights:
  individual: 2.0
  operator: 1.0
  overall: 0.5
```

No code changes required.

---

## Adding a New Rule

Create a new rule class.

Example:

```python
class DriverShiftRule(SoftRule):
    def score(self, context):
        return penalty
```

Register the rule:

```python
rules = [
    IndividualWaitRule(),
    OperatorFairnessRule(),
    DriverShiftRule(),
]
```

No scheduler engine changes are required.

---

## Scheduler Output

For each bus:

* Departure time
* Charging stations selected
* Charge start time
* Charge end time
* Waiting time
* Arrival time

For each station:

* Charging order
* Queue delays
* Utilization timeline

---

## Assumptions

* Constant travel speed
* No traffic variation
* Charging always reaches full battery
* Fixed charging duration (25 minutes)
* All buses have identical battery capacity
* Endpoints provide full pre-trip charging

---

## Future Extensions Supported

The data model supports:

* Additional stations
* Multiple routes
* Multiple chargers per station
* Different battery capacities
* Different charging durations
* Priority buses
* Electricity price optimization
* Driver shift constraints
* Additional operators

without requiring scheduler engine rewrites.

---

## Deployment

Deploy directly to Streamlit Community Cloud:

1. Push repository to GitHub
2. Create Streamlit Cloud app
3. Select repository
4. Deploy

No infrastructure setup required.
