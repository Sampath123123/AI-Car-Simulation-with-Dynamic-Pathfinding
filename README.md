# AI Car Simulation with Dynamic Pathfinding

A car that finds its own way across a city grid — and re-routes when traffic
appears in front of it.

Built with pygame. An A* agent navigates an 80x50 tile world of randomly
generated buildings, continuously re-evaluating its route as traffic jams spawn
and expire around it.

## What it does

- **A\* pathfinding** over a 4000-tile grid with building obstacles
- **Proactive re-routing** — the car re-checks for a better path every 500ms
  rather than only when blocked
- **Dynamic traffic** — congestion spawns at intervals, lives for ~20s, and
  raises the cost of affected tiles
- **Click-to-navigate** — drop a destination marker anywhere and the car
  plans a route to it
- **Zoomable camera** that follows the car through the world

The interesting part is the re-routing: because traffic is added and removed
while the car is already moving, the optimal path changes mid-journey. The
agent handles that instead of committing to its first plan.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Controls

| Action | Input |
| ------ | ----- |
| Set destination | Left click |
| Zoom | Mouse wheel |
| Quit | `Esc` or close window |

## How the pathfinding works

The grid is stored as a 2D cost array. Free tiles cost 1, traffic tiles cost
more, buildings are impassable. A* uses a heap-based priority queue with
Euclidean distance as the heuristic.

Every `PROACTIVE_REROUTE_INTERVAL` the car re-runs A* from its current tile. If
the new path is cheaper than the remaining portion of the current one, it
switches.

## Tuning

Constants at the top of `main.py`:

```python
CAR_SPEED = 3.5
TRAFFIC_GENERATION_INTERVAL = 200   # ms between traffic spawns
TRAFFIC_LIFESPAN = 20000            # ms before a jam clears
MAX_TRAFFIC_STOPS = 60
PROACTIVE_REROUTE_INTERVAL = 500    # ms between route re-checks
```

## Stack

`pygame` · `heapq` (A\*)
