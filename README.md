# AI Dispatcher — Energy-O-Thon 2026 | Team 4678

> **AI Dispatcher for the Energy Transition: Balancing Production and ESG under Uncertainty**

## 🔗 [View Full Documentation →](index.html)

## The Problem

A 500 MW metallurgical plant faces a 90 MW deficit when renewable generation drops by 60% during a weather anomaly. The AI must decide how to blend diesel generators (cheap but dirty) with load shedding (clean but expensive) to minimize total losses.

## Key Results

| Metric | Value |
|---|---|
| Optimal Strategy (β=1.0) | DGU=55 MW, HVAC=5, PUMP=30, MILL=0 |
| Total Loss | **$19,363/hr** |
| CO₂ Emitted | 47.4 tonnes |
| β Flip Point | β=2.6 (strategy completely changes) |

## Project Structure

```
ai-dispatcher/
├── index.html              # Complete documentation page
├── README.md               # This file
├── images/                 # All 9 diagrams
│   ├── diagram_architecture.png
│   ├── diagram_decision_tree.png
│   ├── diagram_dgu_ramp.png
│   ├── diagram_temperature.png
│   ├── diagram_waterfall.png
│   ├── diagram_heatmap.png
│   ├── diagram_radar.png
│   ├── pareto_frontier.png
│   └── beta_sensitivity.png
└── code/                   # All Python scripts
    ├── optimizer.py         # Core optimization solver
    ├── solve_all_methods.py # 3-method verification
    ├── mpc_simulation.py    # Dynamic re-optimization
    ├── generate_diagrams.py # Diagram generation
    └── plot_pareto.py       # Pareto frontier plots
```

## How to Run

```bash
# Install dependencies
pip install numpy scipy matplotlib

# Run the optimizer
python code/optimizer.py

# Run 3-method verification
python code/solve_all_methods.py

# Run MPC simulation (13-hour outage)
python code/mpc_simulation.py

# Generate all diagrams
python code/generate_diagrams.py
```

## Technical Stack

- **Optimization**: Exhaustive enumeration + scipy.optimize.linprog verification
- **Visualization**: Matplotlib with dark theme
- **Physics**: Newton's Law of Cooling, DGU ramp model, graduated penalty zones
- **Architecture**: Model Predictive Control (MPC) with 30-min receding horizon

## License

MIT — Built for Energy-O-Thon 2026
