"""
AI Dispatcher — Complete Diagram Suite
=======================================
Generates 7 publication-quality diagrams for the Energy-O-Thon presentation:

  1. System Architecture Flowchart
  2. DGU Ramp Physics (Two-Phase Timeline)
  3. Temperature Drift & Graduated Penalty Zones
  4. Loss Function Component Breakdown (Waterfall)
  5. Decision Matrix Heatmap
  6. Scenario Comparison Radar Chart
  7. Time-Phased Dispatch Strategy (Stacked Area)

All plots use dark-theme styling for premium presentation look.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe
import numpy as np
import os
import json

# ── Global style ──────────────────────────────────────────────────
DARK_BG = '#0f1923'
PANEL_BG = '#162231'
ACCENT_CYAN = '#00d4ff'
ACCENT_PINK = '#e040fb'
ACCENT_GREEN = '#51cf66'
ACCENT_RED = '#ff6b6b'
ACCENT_ORANGE = '#ffa94d'
ACCENT_YELLOW = '#ffd43b'
TEXT_WHITE = '#e8eaed'
TEXT_DIM = '#8b95a5'
GRID_COLOR = '#2a3a4a'

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def apply_dark_style(fig, ax):
    """Apply consistent dark theme to any axis."""
    fig.patch.set_facecolor(DARK_BG)
    if isinstance(ax, np.ndarray):
        for a in ax.flat:
            _style_ax(a)
    else:
        _style_ax(ax)

def _style_ax(ax):
    ax.set_facecolor(PANEL_BG)
    ax.tick_params(colors=TEXT_WHITE, labelsize=10)
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)
    ax.xaxis.label.set_color(TEXT_WHITE)
    ax.yaxis.label.set_color(TEXT_WHITE)
    ax.title.set_color(TEXT_WHITE)


# ══════════════════════════════════════════════════════════════════
# DIAGRAM 1: SYSTEM ARCHITECTURE FLOWCHART
# ══════════════════════════════════════════════════════════════════
def diagram_architecture():
    """Complete AI Dispatcher architecture as a layered flowchart."""
    fig, ax = plt.subplots(figsize=(18, 12))
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 12)
    ax.axis('off')

    # ── Helper to draw a rounded box ──
    def draw_box(x, y, w, h, text, color, fontsize=9, alpha=0.9, textcolor='white', 
                 style='round,pad=0.3', subtext=None):
        box = FancyBboxPatch((x, y), w, h, boxstyle=style,
                             facecolor=color, edgecolor='white', linewidth=1.2, alpha=alpha)
        ax.add_patch(box)
        ax.text(x + w/2, y + h/2 + (0.12 if subtext else 0), text,
                ha='center', va='center', fontsize=fontsize, fontweight='bold',
                color=textcolor, zorder=10)
        if subtext:
            ax.text(x + w/2, y + h/2 - 0.22, subtext,
                    ha='center', va='center', fontsize=7, color=TEXT_DIM, zorder=10,
                    fontstyle='italic')

    def draw_arrow(x1, y1, x2, y2, color=TEXT_DIM, style='->', linewidth=1.5):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle=style, color=color, lw=linewidth,
                                   connectionstyle='arc3,rad=0'))

    def draw_curved_arrow(x1, y1, x2, y2, color=TEXT_DIM, rad=0.2):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.5,
                                   connectionstyle=f'arc3,rad={rad}'))

    # ── Title ──
    ax.text(9, 11.5, 'AI DISPATCHER — SYSTEM ARCHITECTURE',
            ha='center', va='center', fontsize=18, fontweight='bold',
            color=ACCENT_CYAN, zorder=10,
            path_effects=[pe.withStroke(linewidth=2, foreground=DARK_BG)])
    ax.text(9, 11.1, 'Predictive Energy Management for 90 MW Deficit Response',
            ha='center', va='center', fontsize=10, color=TEXT_DIM)

    # ── LAYER 1: Data Sources (Top) ──
    layer1_y = 9.5
    ax.text(0.5, layer1_y + 0.9, 'LAYER 1: TELEMETRY & IoT',
            fontsize=10, fontweight='bold', color=ACCENT_ORANGE)
    
    sources = [
        (0.5, 'Weather\nStation', '#1a5276', 'Wind, Solar\nIrradiance'),
        (3.2, 'Grid SCADA', '#1a5276', 'Import MW,\nFrequency'),
        (5.9, 'Plant DCS', '#1a5276', 'Load per\nShop Floor'),
        (8.6, 'DGU PLC', '#1a5276', 'Fuel Level,\nTemp, RPM'),
        (11.3, 'HVAC\nSensors', '#1a5276', 'Room Temp,\nAir Quality'),
        (14.0, 'ESG\nMetering', '#1a5276', 'CO2 Flow,\nEmissions'),
    ]
    for sx, name, col, sub in sources:
        draw_box(sx, layer1_y, 2.2, 0.8, name, col, fontsize=8, subtext=sub)

    # ── LAYER 2: Data Pipeline ──
    layer2_y = 7.8
    ax.text(0.5, layer2_y + 0.85, 'LAYER 2: DATA VALIDATION & FUSION',
            fontsize=10, fontweight='bold', color=ACCENT_YELLOW)
    
    draw_box(0.5, layer2_y, 3.5, 0.7, 'Dirty Data Filter', '#6c3483',
             subtext='IQR, z-score, sensor health')
    draw_box(4.5, layer2_y, 3.5, 0.7, 'Multi-Source Fusion', '#6c3483',
             subtext='Kalman filter, confidence voting')
    draw_box(8.5, layer2_y, 3.5, 0.7, 'State Estimator', '#6c3483',
             subtext='Reconstruct missing 20% sensors')
    draw_box(12.5, layer2_y, 4.0, 0.7, 'Real-Time Dashboard', '#1a5276',
             subtext='Grafana / SCADA HMI')

    # Arrows: Layer 1 → Layer 2
    for sx, _, _, _ in sources[:3]:
        draw_arrow(sx + 1.1, layer1_y, 2.25, layer2_y + 0.7, color=ACCENT_CYAN)
    for sx, _, _, _ in sources[3:]:
        draw_arrow(sx + 1.1, layer1_y, 10.25, layer2_y + 0.7, color=ACCENT_CYAN)

    # ── LAYER 3: Predictive Engine ──
    layer3_y = 6.1
    ax.text(0.5, layer3_y + 0.85, 'LAYER 3: PREDICTIVE ANALYTICS (15-MIN HORIZON)',
            fontsize=10, fontweight='bold', color=ACCENT_GREEN)
    
    draw_box(0.5, layer3_y, 3.8, 0.7, 'Weather Forecast Model', '#196f3d',
             subtext='LSTM / Prophet, renewable drop')
    draw_box(4.8, layer3_y, 3.8, 0.7, 'Load Forecast Model', '#196f3d',
             subtext='Process schedule + anomaly')
    draw_box(9.1, layer3_y, 3.8, 0.7, 'Deficit Predictor', '#196f3d',
             subtext='P_demand - P_supply = D(t+15)')
    draw_box(13.4, layer3_y, 3.2, 0.7, 'Confidence\nScorer', '#7d3c98',
             fontsize=8, subtext='Uncertainty bounds')

    # Arrows: Layer 2 → Layer 3
    draw_arrow(2.25, layer2_y, 2.4, layer3_y + 0.7, color=ACCENT_GREEN)
    draw_arrow(6.25, layer2_y, 6.7, layer3_y + 0.7, color=ACCENT_GREEN)
    draw_arrow(10.25, layer2_y, 11.0, layer3_y + 0.7, color=ACCENT_GREEN)

    # ── LAYER 4: DECISION CORE (Central, highlighted) ──
    layer4_y = 3.8
    ax.text(0.5, layer4_y + 1.55, 'LAYER 4: DECISION CORE (OPTIMIZATION ENGINE)',
            fontsize=10, fontweight='bold', color=ACCENT_PINK)
    
    # Main decision box (larger, highlighted)
    decision_box = FancyBboxPatch((2.5, layer4_y), 6.0, 1.4, 
                                  boxstyle='round,pad=0.3',
                                  facecolor='#1a0a2e', edgecolor=ACCENT_PINK,
                                  linewidth=2.5, alpha=0.95)
    ax.add_patch(decision_box)
    ax.text(5.5, layer4_y + 1.05, 'LOSS FUNCTION OPTIMIZER', ha='center',
            fontsize=12, fontweight='bold', color=ACCENT_PINK, zorder=10)
    ax.text(5.5, layer4_y + 0.7, 'min J = C_econ + C_discomfort + C_oprisk + β·C_reputation',
            ha='center', fontsize=8, color=ACCENT_CYAN, zorder=10, family='monospace')
    ax.text(5.5, layer4_y + 0.35, 'Subject to: Power Balance | DGU Ramp | Capacity Limits',
            ha='center', fontsize=7, color=TEXT_DIM, zorder=10)

    # Constraint boxes
    draw_box(9.5, layer4_y + 0.7, 2.5, 0.6, 'DGU Ramp\nConstraint', '#7d3c98',
             fontsize=8, subtext='R(t) = linear 5min')
    draw_box(9.5, layer4_y, 2.5, 0.6, 'Temp Threshold\nPenalty', '#7d3c98',
             fontsize=8, subtext='Normal→Warn→Severe')
    draw_box(12.5, layer4_y + 0.7, 2.5, 0.6, 'β Factor\n(ESG Weight)', '#6c3483',
             fontsize=8, subtext='1.0 normal, 3.0 ESG')
    draw_box(12.5, layer4_y, 2.5, 0.6, 'Critical Process\nGuard', '#922b21',
             fontsize=8, subtext='Electrolysis: NEVER off')

    # Arrows: Layer 3 → Layer 4
    draw_arrow(11.0, layer3_y, 5.5, layer4_y + 1.4, color=ACCENT_PINK)

    # ── LAYER 5: Actuation ──
    layer5_y = 1.8
    ax.text(0.5, layer5_y + 0.85, 'LAYER 5: ACTUATION & DISPATCH',
            fontsize=10, fontweight='bold', color=ACCENT_CYAN)
    
    draw_box(0.3, layer5_y, 2.8, 0.7, 'DGU Start\nCommand', '#922b21',
             fontsize=8, subtext='MW target + ramp rate')
    draw_box(3.5, layer5_y, 2.8, 0.7, 'HVAC Shed\nCommand', '#1a5276',
             fontsize=8, subtext='0-20 MW, proportional')
    draw_box(6.7, layer5_y, 2.8, 0.7, 'Pump Shed\nCommand', '#1a5276',
             fontsize=8, subtext='0-30 MW, proportional')
    draw_box(9.9, layer5_y, 2.8, 0.7, 'Mill Shed\nCommand', '#7d6608',
             fontsize=8, subtext='0-40 MW, proportional')
    draw_box(13.1, layer5_y, 3.5, 0.7, 'Human-in-Loop\nWar Room', '#922b21',
             fontsize=8, subtext='Critical decisions only')

    # Arrows: Layer 4 → Layer 5
    for xd in [1.7, 4.9, 8.1, 11.3]:
        draw_arrow(5.5, layer4_y, xd, layer5_y + 0.7, color=ACCENT_CYAN)

    # ── LAYER 6: Reporting ──
    layer6_y = 0.4
    ax.text(0.5, layer6_y + 0.75, 'LAYER 6: ESG REPORTING & AUDIT',
            fontsize=10, fontweight='bold', color=ACCENT_GREEN)
    
    draw_box(0.5, layer6_y, 3.5, 0.6, 'CO2 Emission Logger', '#196f3d',
             fontsize=8, subtext='Scope 1+2, audit trail')
    draw_box(4.5, layer6_y, 3.5, 0.6, 'Decision Audit Trail', '#196f3d',
             fontsize=8, subtext='Why each action was taken')
    draw_box(8.5, layer6_y, 3.5, 0.6, 'Compliance Report', '#196f3d',
             fontsize=8, subtext='GRI/SASB/TCFD format')
    draw_box(12.5, layer6_y, 4.0, 0.6, 'Pareto Frontier Log', '#196f3d',
             fontsize=8, subtext='Cost vs CO2 for each event')

    # Arrows: Layer 5 → Layer 6
    draw_arrow(5.5, layer5_y, 6.25, layer6_y + 0.6, color=ACCENT_GREEN)

    # ── Feedback loop arrow ──
    draw_curved_arrow(14.5, layer6_y + 0.6, 16.5, layer2_y + 0.35, 
                      color=ACCENT_ORANGE, rad=-0.3)
    ax.text(16.7, 4.5, 'Feedback\nLoop', fontsize=8, color=ACCENT_ORANGE, 
            ha='center', rotation=90)

    plt.savefig(os.path.join(OUTPUT_DIR, 'diagram_architecture.png'),
                dpi=200, facecolor=DARK_BG, bbox_inches='tight')
    plt.close()
    print("[1/7] Architecture diagram saved")


# ══════════════════════════════════════════════════════════════════
# DIAGRAM 2: DGU RAMP PHYSICS (Two-Phase Timeline)
# ══════════════════════════════════════════════════════════════════
def diagram_dgu_ramp():
    """Shows DGU ramp-up timeline with two phases."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), height_ratios=[1.2, 1])
    apply_dark_style(fig, np.array([ax1, ax2]))
    
    t_ramp = 5  # minutes
    t_total = 60  # minutes
    t = np.linspace(0, t_total, 500)
    
    # DGU target = 55 MW (β=1.0 optimal)
    dgu_target = 55
    dgu_power = np.where(t <= t_ramp, dgu_target * t / t_ramp, dgu_target)
    
    # Load shedding during ramp
    deficit = 90
    shed_needed = deficit - dgu_power
    shed_needed = np.maximum(shed_needed, deficit - dgu_target)  # Can't go below Phase 2 level
    
    # Split shedding
    hvac_shed = np.where(t <= t_ramp, 20, 5)   # Max during ramp, optimized after
    pump_shed = np.where(t <= t_ramp, 30, 30)   # Keep pumps shed
    mill_shed = np.where(t <= t_ramp, 40, 0)    # Release mill after ramp
    
    # ── Top Plot: Power Stack ──
    ax1.fill_between(t, 0, dgu_power, color=ACCENT_RED, alpha=0.7, label='DGU Output')
    ax1.fill_between(t, dgu_power, dgu_power + hvac_shed, color=ACCENT_CYAN, alpha=0.5,
                     label='HVAC Shed')
    ax1.fill_between(t, dgu_power + hvac_shed, dgu_power + hvac_shed + pump_shed,
                     color=ACCENT_ORANGE, alpha=0.5, label='Pump Shed')
    ax1.fill_between(t, dgu_power + hvac_shed + pump_shed,
                     dgu_power + hvac_shed + pump_shed + mill_shed,
                     color=ACCENT_YELLOW, alpha=0.5, label='Mill Shed')
    
    # Deficit line
    ax1.axhline(y=deficit, color='white', linestyle='--', linewidth=2, alpha=0.8)
    ax1.text(50, deficit + 2, f'DEFICIT = {deficit} MW', color='white', fontsize=11,
             fontweight='bold')
    
    # Phase markers
    ax1.axvline(x=t_ramp, color=ACCENT_PINK, linestyle=':', linewidth=2, alpha=0.8)
    ax1.text(t_ramp/2, 95, 'PHASE 1\n(RAMP)', ha='center', fontsize=10,
             fontweight='bold', color=ACCENT_PINK,
             bbox=dict(boxstyle='round', facecolor=DARK_BG, edgecolor=ACCENT_PINK, alpha=0.9))
    ax1.text((t_ramp + t_total)/2, 95, 'PHASE 2 (STEADY STATE)', ha='center',
             fontsize=10, fontweight='bold', color=ACCENT_GREEN,
             bbox=dict(boxstyle='round', facecolor=DARK_BG, edgecolor=ACCENT_GREEN, alpha=0.9))
    
    # DGU ramp annotation
    ax1.annotate('DGU ramps\n0 → 55 MW\n(5 minutes)', xy=(2.5, 25), fontsize=9,
                 color='white', ha='center',
                 bbox=dict(boxstyle='round', facecolor='#922b21', alpha=0.8))
    ax1.annotate('Mill released\n(most expensive shed)', xy=(7, 70), fontsize=9,
                 color=ACCENT_YELLOW, ha='left',
                 xytext=(15, 80), textcoords='data',
                 arrowprops=dict(arrowstyle='->', color=ACCENT_YELLOW))
    
    ax1.set_ylabel('Power (MW)', fontsize=12, fontweight='bold')
    ax1.set_title('DGU Warm-Up Physics: Two-Phase Dispatch Strategy', fontsize=14,
                  fontweight='bold', pad=15)
    ax1.legend(loc='right', fontsize=10, facecolor=PANEL_BG, edgecolor=GRID_COLOR,
               labelcolor=TEXT_WHITE)
    ax1.set_xlim(0, t_total)
    ax1.set_ylim(0, 105)
    ax1.grid(True, alpha=0.15, color='white', linestyle='--')
    
    # ── Bottom Plot: Cost Rate Over Time ──
    # Cost rates ($/hr) at each instant
    dgu_cost_rate = 150 * dgu_power + 81 * dgu_power  # fuel + carbon at β=1
    hvac_cost_rate = 3000 * hvac_shed / 20
    pump_cost_rate = 5000 * pump_shed / 30
    mill_cost_rate = 15000 * mill_shed / 40
    total_cost_rate = dgu_cost_rate + hvac_cost_rate + pump_cost_rate + mill_cost_rate
    
    ax2.fill_between(t, 0, dgu_cost_rate, color=ACCENT_RED, alpha=0.6, label='DGU (fuel+CO₂)')
    ax2.fill_between(t, dgu_cost_rate, dgu_cost_rate + hvac_cost_rate,
                     color=ACCENT_CYAN, alpha=0.5, label='HVAC Penalty')
    ax2.fill_between(t, dgu_cost_rate + hvac_cost_rate,
                     dgu_cost_rate + hvac_cost_rate + pump_cost_rate,
                     color=ACCENT_ORANGE, alpha=0.5, label='Pump Loss')
    ax2.fill_between(t, dgu_cost_rate + hvac_cost_rate + pump_cost_rate,
                     total_cost_rate, color=ACCENT_YELLOW, alpha=0.5, label='Mill Loss')
    
    ax2.plot(t, total_cost_rate, color='white', linewidth=2, alpha=0.8, label='Total Cost Rate')
    
    # Phase marker
    ax2.axvline(x=t_ramp, color=ACCENT_PINK, linestyle=':', linewidth=2, alpha=0.8)
    
    # Annotate cost spike during ramp
    max_cost_ramp = total_cost_rate[0]
    steady_cost = total_cost_rate[-1]
    ax2.annotate(f'Ramp spike: ${max_cost_ramp:,.0f}/hr\n(all loads shed)',
                 xy=(0.5, max_cost_ramp), fontsize=9, color='white',
                 xytext=(10, max_cost_ramp - 2000), textcoords='data',
                 arrowprops=dict(arrowstyle='->', color='white'),
                 bbox=dict(boxstyle='round', facecolor=DARK_BG, alpha=0.8))
    ax2.annotate(f'Steady: ${steady_cost:,.0f}/hr',
                 xy=(40, steady_cost), fontsize=9, color=ACCENT_GREEN,
                 xytext=(42, steady_cost + 5000), textcoords='data',
                 arrowprops=dict(arrowstyle='->', color=ACCENT_GREEN),
                 bbox=dict(boxstyle='round', facecolor=DARK_BG, alpha=0.8))
    
    ax2.set_xlabel('Time (minutes)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Cost Rate ($/hour)', fontsize=12, fontweight='bold')
    ax2.set_title('Instantaneous Cost Rate During Crisis', fontsize=14,
                  fontweight='bold', pad=10)
    ax2.legend(loc='upper right', fontsize=9, facecolor=PANEL_BG, edgecolor=GRID_COLOR,
               labelcolor=TEXT_WHITE)
    ax2.set_xlim(0, t_total)
    ax2.grid(True, alpha=0.15, color='white', linestyle='--')
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'diagram_dgu_ramp.png'),
                dpi=200, facecolor=DARK_BG, bbox_inches='tight')
    plt.close()
    print("[2/7] DGU ramp physics diagram saved")


# ══════════════════════════════════════════════════════════════════
# DIAGRAM 3: TEMPERATURE DRIFT & PENALTY ZONES
# ══════════════════════════════════════════════════════════════════
def diagram_temperature():
    """Visualize temperature drift and graduated penalty zones."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    apply_dark_style(fig, np.array([ax1, ax2]))
    
    # ── Left: Temperature Drift Over Time ──
    t = np.linspace(0, 60, 300)  # minutes
    tau = 45  # minutes, thermal time constant
    
    # Blizzard scenario
    T_set = 22
    T_amb_blizzard = -10
    T_room_blizzard = T_amb_blizzard + (T_set - T_amb_blizzard) * np.exp(-t / tau)
    
    # Monsoon scenario
    T_amb_monsoon = 42
    T_room_monsoon = T_amb_monsoon + (T_set - T_amb_monsoon) * np.exp(-t / tau)
    
    ax1.plot(t, T_room_blizzard, color=ACCENT_CYAN, linewidth=2.5, label='Blizzard (T_amb = -10°C)')
    ax1.plot(t, T_room_monsoon, color=ACCENT_RED, linewidth=2.5, label='Monsoon (T_amb = 42°C)')
    
    # Threshold lines (blizzard)
    ax1.axhline(y=16, color=ACCENT_YELLOW, linestyle='--', alpha=0.7)
    ax1.text(62, 16, 'Warning\n(16°C)', fontsize=8, color=ACCENT_YELLOW, va='center')
    ax1.axhline(y=9, color=ACCENT_RED, linestyle='--', alpha=0.7)
    ax1.text(62, 9, 'CRITICAL\n(9°C)', fontsize=8, color=ACCENT_RED, va='center')
    
    # Threshold lines (monsoon)
    ax1.axhline(y=28, color=ACCENT_YELLOW, linestyle=':', alpha=0.7)
    ax1.text(62, 28, 'Warning\n(28°C)', fontsize=8, color=ACCENT_YELLOW, va='center')
    ax1.axhline(y=35, color=ACCENT_RED, linestyle=':', alpha=0.7)
    ax1.text(62, 35, 'CRITICAL\n(35°C)', fontsize=8, color=ACCENT_RED, va='center')
    
    # Normal zone shading
    ax1.axhspan(16, 28, alpha=0.08, color=ACCENT_GREEN)
    ax1.text(30, 22, 'NORMAL ZONE', fontsize=10, color=ACCENT_GREEN, ha='center',
             fontweight='bold', alpha=0.7)
    
    # Warning shading (blizzard)
    ax1.axhspan(9, 16, alpha=0.08, color=ACCENT_YELLOW)
    ax1.axhspan(28, 35, alpha=0.08, color=ACCENT_YELLOW)
    
    ax1.set_xlabel('Time Since HVAC Disconnection (min)', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Room Temperature (°C)', fontsize=11, fontweight='bold')
    ax1.set_title('Temperature Drift After HVAC Shed\n(Newton\'s Law of Cooling, τ = 45 min)',
                  fontsize=12, fontweight='bold', pad=10)
    ax1.legend(fontsize=10, facecolor=PANEL_BG, edgecolor=GRID_COLOR, labelcolor=TEXT_WHITE)
    ax1.set_xlim(0, 65)
    ax1.set_ylim(-5, 45)
    ax1.grid(True, alpha=0.15, color='white', linestyle='--')
    
    # ── Right: Penalty Zone Diagram ──
    # Show penalty as function of temperature deviation
    deviation = np.linspace(0, 20, 200)
    T_warn_delta = 6
    T_crit_delta = 13
    
    penalty = np.zeros_like(deviation)
    for i, d in enumerate(deviation):
        if d <= T_warn_delta:
            penalty[i] = 3000  # base only
        elif d <= T_crit_delta:
            frac = (d - T_warn_delta) / (T_crit_delta - T_warn_delta)
            penalty[i] = 3000 + 3000 * frac
        else:
            penalty[i] = 3000 + 3000 + 8000  # severe

    # Color-coded zones
    mask_normal = deviation <= T_warn_delta
    mask_warn = (deviation > T_warn_delta) & (deviation <= T_crit_delta)
    mask_severe = deviation > T_crit_delta
    
    ax2.fill_between(deviation[mask_normal], 0, penalty[mask_normal], 
                     color=ACCENT_GREEN, alpha=0.4, label='Normal Zone')
    ax2.fill_between(deviation[mask_warn], 0, penalty[mask_warn],
                     color=ACCENT_YELLOW, alpha=0.4, label='Warning Zone')
    ax2.fill_between(deviation[mask_severe], 0, penalty[mask_severe],
                     color=ACCENT_RED, alpha=0.4, label='Severe Zone')
    
    ax2.plot(deviation, penalty, color='white', linewidth=2.5)
    
    # Annotations
    ax2.annotate('$3,000/hr\n(base cost)', xy=(3, 3000), fontsize=9,
                 color=ACCENT_GREEN, fontweight='bold',
                 xytext=(1, 5000), textcoords='data',
                 arrowprops=dict(arrowstyle='->', color=ACCENT_GREEN))
    ax2.annotate('Linear ramp\n+$3,000', xy=(9.5, 4500), fontsize=9,
                 color=ACCENT_YELLOW, fontweight='bold',
                 xytext=(8, 7000), textcoords='data',
                 arrowprops=dict(arrowstyle='->', color=ACCENT_YELLOW))
    ax2.annotate('STEP PENALTY\n+$8,000/hr\n(safety violation)', xy=(15, 14000),
                 fontsize=9, color=ACCENT_RED, fontweight='bold',
                 xytext=(14, 11000), textcoords='data',
                 arrowprops=dict(arrowstyle='->', color=ACCENT_RED))
    
    # Zone boundaries
    ax2.axvline(x=T_warn_delta, color=ACCENT_YELLOW, linestyle='--', linewidth=1.5)
    ax2.axvline(x=T_crit_delta, color=ACCENT_RED, linestyle='--', linewidth=1.5)
    
    ax2.set_xlabel('Temperature Deviation from Setpoint (°C)', fontsize=11, fontweight='bold')
    ax2.set_ylabel('HVAC Penalty ($/hour)', fontsize=11, fontweight='bold')
    ax2.set_title('Graduated HVAC Penalty Structure\n(3 Penalty Zones)',
                  fontsize=12, fontweight='bold', pad=10)
    ax2.legend(fontsize=10, facecolor=PANEL_BG, edgecolor=GRID_COLOR, labelcolor=TEXT_WHITE,
               loc='upper left')
    ax2.grid(True, alpha=0.15, color='white', linestyle='--')
    ax2.set_xlim(0, 20)
    ax2.set_ylim(0, 16000)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'diagram_temperature.png'),
                dpi=200, facecolor=DARK_BG, bbox_inches='tight')
    plt.close()
    print("[3/7] Temperature drift & penalty diagram saved")


# ══════════════════════════════════════════════════════════════════
# DIAGRAM 4: LOSS FUNCTION WATERFALL CHART
# ══════════════════════════════════════════════════════════════════
def diagram_waterfall():
    """Waterfall chart showing loss function component buildup for 3 strategies."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 7), sharey=True)
    apply_dark_style(fig, axes)
    
    strategies = [
        {
            'name': 'Strategy A: ALL DGU (90 MW)',
            'components': [
                ('DGU Fuel', 12938, ACCENT_RED),
                ('DGU CO₂\n(β=1)', 6986, ACCENT_PINK),
                ('HVAC\n(Phase 1)', 250, ACCENT_CYAN),
                ('Pump\n(Phase 1)', 417, ACCENT_ORANGE),
                ('Mill\n(Phase 1)', 1250, ACCENT_YELLOW),
            ],
            'total': 21841,
            'co2': '77.6t CO₂'
        },
        {
            'name': 'Strategy B: DGU(55)+PUMP(30)+HVAC(5)',
            'components': [
                ('DGU Fuel', 7906, ACCENT_RED),
                ('DGU CO₂\n(β=1)', 4269, ACCENT_PINK),
                ('HVAC\n(base)', 1669, ACCENT_CYAN),
                ('Pump\nLoss', 5000, ACCENT_ORANGE),
                ('Mill\n(Phase 1)', 519, ACCENT_YELLOW),
            ],
            'total': 19363,
            'co2': '47.4t CO₂'
        },
        {
            'name': 'Strategy C: DGU(10)+PUMP(30)+MILL(40)',
            'components': [
                ('DGU Fuel', 1438, ACCENT_RED),
                ('DGU CO₂\n(β=1)', 776, ACCENT_PINK),
                ('HVAC', 2584, ACCENT_CYAN),
                ('Pump\nLoss', 5000, ACCENT_ORANGE),
                ('Mill\nLoss', 16320, ACCENT_YELLOW),
            ],
            'total': 26118,
            'co2': '8.6t CO₂'
        },
    ]
    
    for ax, strat in zip(axes, strategies):
        names = [c[0] for c in strat['components']]
        values = [c[1] for c in strat['components']]
        colors = [c[2] for c in strat['components']]
        
        # Waterfall
        cumulative = 0
        for i, (name, val, col) in enumerate(strat['components']):
            ax.bar(i, val, bottom=cumulative, color=col, edgecolor='white',
                   linewidth=0.5, width=0.7, alpha=0.85)
            if val > 1000:
                ax.text(i, cumulative + val/2, f'${val:,.0f}', ha='center', va='center',
                        fontsize=7, color='white', fontweight='bold')
            cumulative += val
        
        # Total bar
        ax.bar(len(names), cumulative, color='white', edgecolor='white',
               linewidth=1, width=0.7, alpha=0.2)
        ax.bar(len(names), cumulative, color='none', edgecolor='white',
               linewidth=2, width=0.7)
        ax.text(len(names), cumulative + 300, f'${cumulative:,.0f}/hr',
                ha='center', fontsize=11, fontweight='bold', color='white')
        ax.text(len(names), cumulative - 1500, strat['co2'],
                ha='center', fontsize=9, fontweight='bold', 
                color=ACCENT_GREEN if '8.6' in strat['co2'] else ACCENT_RED)
        
        ax.set_xticks(range(len(names) + 1))
        ax.set_xticklabels(names + ['TOTAL'], fontsize=8, rotation=0)
        ax.set_title(strat['name'], fontsize=10, fontweight='bold', pad=10)
        ax.grid(True, alpha=0.1, color='white', axis='y', linestyle='--')
    
    axes[0].set_ylabel('Cost ($/hour)', fontsize=12, fontweight='bold')
    
    fig.suptitle('Loss Function Breakdown: Three Dispatch Strategies (β=1.0)',
                 fontsize=14, fontweight='bold', color=TEXT_WHITE, y=1.02)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'diagram_waterfall.png'),
                dpi=200, facecolor=DARK_BG, bbox_inches='tight')
    plt.close()
    print("[4/7] Waterfall cost breakdown saved")


# ══════════════════════════════════════════════════════════════════
# DIAGRAM 5: DECISION MATRIX HEATMAP
# ══════════════════════════════════════════════════════════════════
def diagram_heatmap():
    """Heatmap showing total cost across DGU and shedding combinations."""
    fig, ax = plt.subplots(figsize=(14, 9))
    apply_dark_style(fig, ax)
    
    # Load pareto data to get all solutions
    pareto_file = os.path.join(OUTPUT_DIR, 'pareto_data.json')
    
    # Generate cost matrix: DGU (x-axis) vs Total Shed Composition  
    dgu_values = list(range(0, 91, 10))
    
    # For each DGU level, find optimal shedding mix
    # We'll show cost as f(DGU, β)
    beta_values = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
    
    cost_matrix = np.zeros((len(beta_values), len(dgu_values)))
    
    for i, beta in enumerate(beta_values):
        for j, dgu in enumerate(dgu_values):
            remaining = max(0, 90 - dgu)
            if remaining > 90:  # infeasible
                cost_matrix[i, j] = np.nan
                continue
            
            # Greedy allocation of remaining: HVAC first (cheapest), then PUMP, then MILL
            hvac = min(20, remaining)
            remaining -= hvac
            pump = min(30, remaining)
            remaining -= pump
            mill = min(40, remaining)
            remaining -= mill
            
            if remaining > 0:
                cost_matrix[i, j] = np.nan
                continue
            
            # Calculate cost (simplified steady-state)
            fuel = 150 * dgu
            carbon = beta * 81 * dgu
            hvac_c = 3000 * hvac / 20
            pump_c = 5000 * pump / 30
            mill_c = 15000 * mill / 40
            cost_matrix[i, j] = fuel + carbon + hvac_c + pump_c + mill_c
    
    # Plot heatmap
    im = ax.imshow(cost_matrix, cmap='RdYlGn_r', aspect='auto', interpolation='nearest')
    
    # Add text annotations
    for i in range(len(beta_values)):
        for j in range(len(dgu_values)):
            val = cost_matrix[i, j]
            if not np.isnan(val):
                color = 'white' if val > 25000 or val < 15000 else 'black'
                ax.text(j, i, f'${val/1000:.1f}k', ha='center', va='center',
                        fontsize=8, color=color, fontweight='bold')
    
    # Mark minimum per row
    for i in range(len(beta_values)):
        row = cost_matrix[i, :]
        valid = ~np.isnan(row)
        if valid.any():
            j_min = np.nanargmin(row)
            ax.add_patch(plt.Rectangle((j_min - 0.5, i - 0.5), 1, 1,
                                        fill=False, edgecolor=ACCENT_CYAN, linewidth=3))
    
    ax.set_xticks(range(len(dgu_values)))
    ax.set_xticklabels([f'{d} MW' for d in dgu_values])
    ax.set_yticks(range(len(beta_values)))
    ax.set_yticklabels([f'β = {b:.1f}' for b in beta_values])
    
    ax.set_xlabel('DGU Dispatch (MW)', fontsize=12, fontweight='bold', color=TEXT_WHITE)
    ax.set_ylabel('ESG Weight (β)', fontsize=12, fontweight='bold', color=TEXT_WHITE)
    ax.set_title('Decision Matrix: Steady-State Cost ($/hr) by DGU Level and β\n'
                 '(Cyan border = optimal for that β)',
                 fontsize=13, fontweight='bold', color=TEXT_WHITE, pad=15)
    
    cbar = fig.colorbar(im, ax=ax, shrink=0.8, label='Total Cost ($/hr)')
    cbar.ax.yaxis.label.set_color(TEXT_WHITE)
    cbar.ax.tick_params(colors=TEXT_WHITE)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'diagram_heatmap.png'),
                dpi=200, facecolor=DARK_BG, bbox_inches='tight')
    plt.close()
    print("[5/7] Decision matrix heatmap saved")


# ══════════════════════════════════════════════════════════════════
# DIAGRAM 6: SCENARIO COMPARISON RADAR CHART
# ══════════════════════════════════════════════════════════════════
def diagram_radar():
    """Radar chart comparing scenarios across multiple dimensions."""
    
    categories = ['Financial\nCost', 'CO₂\nEmissions', 'Production\nImpact',
                  'Human\nComfort', 'Startup\nRisk', 'ESG\nScore']
    N = len(categories)
    
    # Scenarios (normalized 0-10, where 10 = worst)
    scenarios = {
        'All DGU (90 MW)': [3, 10, 1, 1, 3, 10],
        'DGU(55)+PUMP(30)': [4, 6, 5, 1, 2, 6],
        'DGU(10)+Shed(80)': [7, 1, 8, 3, 1, 1],
        'All Shedding': [9, 0, 10, 5, 0, 0],
    }
    
    colors = [ACCENT_RED, ACCENT_CYAN, ACCENT_GREEN, ACCENT_YELLOW]
    
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)
    
    for (name, values), color in zip(scenarios.items(), colors):
        values_plot = values + values[:1]
        ax.plot(angles, values_plot, 'o-', linewidth=2, label=name, color=color, markersize=6)
        ax.fill(angles, values_plot, alpha=0.1, color=color)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=11, fontweight='bold', color=TEXT_WHITE)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(['2', '4', '6', '8', '10'], fontsize=8, color=TEXT_DIM)
    ax.set_ylim(0, 10)
    
    # Style
    ax.spines['polar'].set_color(GRID_COLOR)
    ax.tick_params(colors=TEXT_WHITE)
    ax.grid(True, color=GRID_COLOR, alpha=0.3)
    
    ax.set_title('Multi-Dimensional Strategy Comparison\n(Higher = Worse Impact)',
                 fontsize=14, fontweight='bold', color=TEXT_WHITE, pad=30)
    
    legend = ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=10,
                       facecolor=PANEL_BG, edgecolor=GRID_COLOR, labelcolor=TEXT_WHITE)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'diagram_radar.png'),
                dpi=200, facecolor=DARK_BG, bbox_inches='tight')
    plt.close()
    print("[6/7] Radar comparison chart saved")


# ══════════════════════════════════════════════════════════════════
# DIAGRAM 7: COMPLETE DECISION TREE FLOWCHART
# ══════════════════════════════════════════════════════════════════
def diagram_decision_tree():
    """Decision tree showing how the AI Dispatcher chooses actions."""
    fig, ax = plt.subplots(figsize=(18, 11))
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 11)
    ax.axis('off')
    
    def draw_box(x, y, w, h, text, color, fontsize=9, subtext=None, shape='round'):
        style = 'round,pad=0.3' if shape == 'round' else 'sawtooth,pad=0.3'
        box = FancyBboxPatch((x, y), w, h, boxstyle=style,
                             facecolor=color, edgecolor='white', linewidth=1.2, alpha=0.9)
        ax.add_patch(box)
        ax.text(x + w/2, y + h/2 + (0.1 if subtext else 0), text,
                ha='center', va='center', fontsize=fontsize, fontweight='bold',
                color='white', zorder=10)
        if subtext:
            ax.text(x + w/2, y + h/2 - 0.18, subtext,
                    ha='center', va='center', fontsize=7, color=TEXT_DIM, zorder=10)
    
    def draw_diamond(cx, cy, w, h, text, color):
        diamond = plt.Polygon([(cx, cy+h/2), (cx+w/2, cy), (cx, cy-h/2), (cx-w/2, cy)],
                              facecolor=color, edgecolor='white', linewidth=1.5, alpha=0.9)
        ax.add_patch(diamond)
        ax.text(cx, cy, text, ha='center', va='center', fontsize=8,
                fontweight='bold', color='white', zorder=10)
    
    def arrow(x1, y1, x2, y2, label=None, color=TEXT_DIM):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.8))
        if label:
            mx, my = (x1+x2)/2, (y1+y2)/2
            ax.text(mx, my + 0.15, label, fontsize=7, color=color,
                    ha='center', fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.15', facecolor=DARK_BG, alpha=0.9))
    
    # Title
    ax.text(9, 10.6, 'AI DISPATCHER — DECISION TREE',
            ha='center', fontsize=16, fontweight='bold', color=ACCENT_CYAN)
    ax.text(9, 10.25, 'Real-Time Decision Logic for Deficit Response',
            ha='center', fontsize=10, color=TEXT_DIM)
    
    # ── Level 1: Trigger ──
    draw_box(6.5, 9.2, 5, 0.7, 'DEFICIT DETECTED: D = P_demand − P_supply > 0',
             '#1a5276', fontsize=10, subtext='Predicted 15 min ahead via LSTM/Prophet')
    
    # ── Level 2: Validate ──
    draw_diamond(9, 8.0, 3.5, 0.8, 'Sensor data\nreliable?', '#6c3483')
    arrow(9, 9.2, 9, 8.4)
    
    # No branch → dirty data handling
    draw_box(13, 7.6, 3.5, 0.7, 'DIRTY DATA HANDLER', '#922b21', fontsize=9,
             subtext='IQR filter + Kalman fallback')
    arrow(10.75, 8.0, 13, 8.0, label='NO (>20% failure)', color=ACCENT_RED)
    arrow(14.75, 7.6, 14.75, 7.0)
    draw_box(13, 6.3, 3.5, 0.7, 'Use estimated state\n+ widen confidence interval',
             '#7d3c98', fontsize=8)
    arrow(14.75, 6.3, 9, 6.8, color=ACCENT_ORANGE)
    
    # Yes branch
    arrow(9, 7.6, 9, 7.0, label='YES', color=ACCENT_GREEN)
    
    # ── Level 3: Check critical ──
    draw_diamond(9, 6.3, 4, 0.8, 'D > max shed?\n(90 MW > 90 MW?)', '#7d3c98')
    arrow(9, 7.0, 9, 6.7)
    
    # Yes → must use DGU
    draw_box(2, 5.8, 3.2, 0.7, 'CRITICAL ALERT\nDGU Required', '#922b21', fontsize=9,
             subtext='Cannot be avoided')
    arrow(7, 6.3, 5.2, 6.2, label='YES', color=ACCENT_RED)
    
    # No → optimize
    arrow(9, 5.9, 9, 5.2, label='NO (feasible)', color=ACCENT_GREEN)
    
    # ── Level 4: Optimization ──
    draw_box(5.5, 4.3, 7, 0.8, 'LOSS FUNCTION OPTIMIZATION ENGINE\n'
             'min J = C_econ + C_discomfort + C_oprisk + β·C_reputation',
             '#1a0a2e', fontsize=9)
    # Border highlight
    box = FancyBboxPatch((5.5, 4.3), 7, 0.8, boxstyle='round,pad=0.3',
                         facecolor='none', edgecolor=ACCENT_PINK, linewidth=2.5)
    ax.add_patch(box)
    
    # Constraint inputs
    draw_box(0.3, 4.3, 2.5, 0.7, 'β Factor\n(ESG context)', '#6c3483', fontsize=8,
             subtext='1.0-3.0 dynamic')
    arrow(2.8, 4.65, 5.5, 4.65, color=ACCENT_PINK)
    
    draw_box(14, 4.3, 3, 0.7, 'DGU Ramp R(t)\n+ Capacity Limits', '#6c3483', fontsize=8,
             subtext='Physics constraints')
    arrow(14, 4.65, 12.5, 4.65, color=ACCENT_PINK)
    
    # ── Level 5: Output decisions ──
    arrow(9, 4.3, 9, 3.5)
    
    draw_diamond(9, 2.8, 4, 0.8, 'Requires human\napproval?', '#7d6608')
    
    # No → auto dispatch
    arrow(7, 2.8, 3.5, 2.5, label='NO (within AI authority)', color=ACCENT_GREEN)
    
    # ── Level 6: Actions ──
    actions_y = 1.2
    draw_box(0.3, actions_y, 2.5, 0.8, 'START DGU\nTarget: x_DGU MW', '#922b21',
             fontsize=8, subtext='5-min ramp begins')
    draw_box(3.2, actions_y, 2.5, 0.8, 'SHED HVAC\n0-20 MW', '#1a5276',
             fontsize=8, subtext='Proportional control')
    draw_box(6.1, actions_y, 2.5, 0.8, 'SHED PUMP\n0-30 MW', '#1a5276',
             fontsize=8, subtext='Rate reduction')
    draw_box(9.0, actions_y, 2.5, 0.8, 'SHED MILL\n0-40 MW', '#7d6608',
             fontsize=8, subtext='Underproduction penalty')
    
    # Yes → human in loop
    arrow(11, 2.8, 14, 2.5, label='YES (critical)', color=ACCENT_RED)
    draw_box(12.5, actions_y, 4.5, 0.8, 'WAR ROOM ESCALATION\nPresent 3 options with costs',
             '#922b21', fontsize=9, subtext='Human approves in < 60 sec')
    
    # Connect to actions
    for x_center in [1.55, 4.45, 7.35, 10.25]:
        arrow(3.5, 2.5, x_center, actions_y + 0.8, color=ACCENT_CYAN)
    
    # ── Feedback: Monitor & Adjust ──
    draw_box(0.3, 0.15, 16.7, 0.6, 'CONTINUOUS MONITORING → Re-optimize every 30 seconds → '
             'Reconnect loads as DGU ramps up → Log CO₂ for ESG audit',
             '#196f3d', fontsize=9)
    
    for x_center in [1.55, 4.45, 7.35, 10.25, 14.75]:
        arrow(x_center, actions_y, x_center, 0.75, color=ACCENT_GREEN)
    
    plt.savefig(os.path.join(OUTPUT_DIR, 'diagram_decision_tree.png'),
                dpi=200, facecolor=DARK_BG, bbox_inches='tight')
    plt.close()
    print("[7/7] Decision tree flowchart saved")


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Generating 7 diagrams for AI Dispatcher presentation...")
    print(f"Output directory: {OUTPUT_DIR}\n")
    
    diagram_architecture()
    diagram_dgu_ramp()
    diagram_temperature()
    diagram_waterfall()
    diagram_heatmap()
    diagram_radar()
    diagram_decision_tree()
    
    print(f"\nAll 7 diagrams saved to: {OUTPUT_DIR}")
    print("\nFiles generated:")
    for f in ['diagram_architecture.png', 'diagram_dgu_ramp.png', 'diagram_temperature.png',
              'diagram_waterfall.png', 'diagram_heatmap.png', 'diagram_radar.png',
              'diagram_decision_tree.png']:
        path = os.path.join(OUTPUT_DIR, f)
        if os.path.exists(path):
            size_kb = os.path.getsize(path) / 1024
            print(f"  [OK] {f} ({size_kb:.0f} KB)")
        else:
            print(f"  [FAIL] {f}")
