Electric Bus Generator App

Overview
This Project implement a scheduling System for electric buses operating from bangalore to Kochi.

The scheduler determines:
Which charging stations each bus should go
The order in which buses access chargers
waiting times at charging stations
Final Arrival times

The System is designed around three Principles:
Correctness
Scalability

Architecture Flow:
Potential Future Work in this Project
More Stations
More Chargers per station
Additional Routes
Different battery Capabilites
Priority buses
Electricity Pricing
Driver Shift Constraints

High Level atrocities
I fetch the Json data
Scenario Loader
Scheduling Engine
        Route Model
        Charging Planner
        Station Queue Manage
        Rule Engine
        validation Engine


Scheduling Framework
Approach Chosen

Custom Event-Driven Scheduling Heuristic

The scheduler uses:

Discrete-event simulation
Station resource scheduling
Weighted rule scoring

This was selected because:

Easy to explain
Easy to extend
Supports changing business rules
Scales better than brute force