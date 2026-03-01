# Planarity

A planar graph untangling puzzle game. You're given a planar graph with scrambled node positions — drag the nodes to eliminate all edge crossings.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Pygame](https://img.shields.io/badge/Pygame-2.6+-green)

## How to play

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python game.py
```

**Controls:**
- **Mouse drag** — move nodes
- **R** — restart level
- **N** — next level (after solving)
- **Q / Esc** — quit

## Levels

10 levels from 5 to 40 nodes. Graphs are generated via incremental face subdivision (guaranteeing planarity), then scrambled. Fewer edges are removed at higher levels, making them denser and harder.

## How it works

- Graphs are built by starting with a triangle and repeatedly subdividing a random face — this always produces a valid planar graph
- Non-bridge edges are optionally removed to make easier puzzles
- Edge crossings are detected using a cross-product orientation test
- During drag, only edges incident to the moved node are rechecked (O(E*deg) instead of O(E^2))
