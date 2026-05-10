*This project has been created as part of the 42 curriculum by sloubiat.*

# Fly-in

## Description
**Fly-in** is an optimization and simulation project developed in Python. The core objective is to route a fleet of drones through a network of zones, moving them from a `start_hub` to an `end_hub` in the minimum number of simulation turns.

The project challenges the developer to manage complex constraints:
* **Dynamic Capacities:** Zones and connections have strict occupancy limits.
* **Movement Costs:** Different terrains (Normal, Restricted, Priority) affect travel time.
* **Conflict Resolution:** Drones must move simultaneously without exceeding capacity or causing deadlocks.
* **Strict Standards:** The entire engine is built using Object-Oriented Programming (OOP) and is fully typesafe.

# Instructions

## Prerequisites
* Python 3.10 or later
* Make

## Installation
Install dependencies and set up the environment:
```
make install
```

## Execution
Run the simulation by providing a map file via standard input:

```
uv run python main.py maps/01_linear_path.txt
```
OR
```
make run ARG='maps/01_linear_path.txt'
```
Development & Linting
To ensure the code meets the mandatory quality and typing standards:

```
make lint
```
For stricter type checking: make lint-strict.

## Algorithm & Implementation Strategy
To achieve high performance and meet the benchmark targets, the following strategies were implemented:

Pathfinding Logic: A modified search algorithm that calculates the "cost-to-goal" for every zone, taking into account the 2-turn cost for restricted zones and favoring priority zones.

Turn-Based Scheduling: At each turn, the engine prioritizes drones based on their remaining path distance. It evaluates potential moves and only commits if the destination's capacity and the connection's capacity are both available.

Simultaneous Movement Rules: The simulation engine follows the rule that drones moving out of a zone free up space for drones moving in during the same turn, maximizing throughput.

Conflict Prevention: A look-ahead mechanism prevents drones from entering a restricted zone connection if they cannot be accommodated in the destination zone upon arrival.

## Visual Representation
Tkinter GUI: Using the pre-calculated simulation history, the project features a graphical interface built with Tkinter. This allowed for:

A smooth visual playback of the drone fleet's movements.

Interactive map exploration.

A clear overview of zone occupancies and connection loads.

# Resources
Python Type Hinting: Typing Module Documentation

Graph Theory: General principles of shortest path algorithms (Dijkstra).

PEP 257: Python Docstring Conventions.

# AI Usage
Ia was used to help me to generate the Readme file
