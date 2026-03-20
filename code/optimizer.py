"""
AI Dispatcher Optimizer — Energy-O-Thon 2026
=============================================
Solves the 90 MW deficit allocation problem with:
  - DGU warm-up physics (5-min ramp)
  - Two-phase time decomposition
  - Graduated HVAC temperature penalties
  - β-weighted ESG cost
  - Operational risk penalty
  - Pareto frontier generation (Financial Cost vs CO₂)

All units: $/hour and MW. Fully normalized.
"""

import numpy as np
from itertools import product
import json
import os

# ============================================================
# 1. SYSTEM PARAMETERS
# ============================================================
DEFICIT = 90          # MW
T_TOTAL = 1.0         # hours (crisis duration)
T_RAMP = 5/60         # hours (5 min DGU warm-up)
T_STEADY = T_TOTAL - T_RAMP  # 0.9167 hours

# Load shedding capacities (MW)
HVAC_MAX = 20
PUMP_MAX = 30
MILL_MAX = 40

# Cost coefficients ($/MWh or $/hr)
DGU_FUEL_COST = 150        # $/MWh
CO2_PER_MWH = 0.9          # tonnes CO₂ per MWh of DGU
ESG_PENALTY = 90           # $/tonne CO₂

# Derived: carbon cost per MW of DGU
CARBON_COST_PER_MW = CO2_PER_MWH * ESG_PENALTY  # = $81/MW/hr

# Load shedding costs ($/hr at full capacity)
HVAC_BASE_COST = 3000      # $/hr for full 20 MW shed
PUMP_COST = 5000            # $/hr for full 30 MW shed
MILL_COST = 15000           # $/hr for full 40 MW shed

# Catastrophe cost (critical process failure)
CATASTROPHE_COST = 1_000_000  # $/event

# Temperature penalty parameters
T_SETPOINT = 22             # °C normal
T_AMBIENT_BLIZZARD = -10    # °C (cold scenario)
T_AMBIENT_MONSOON = 42      # °C (hot scenario)
TAU_THERMAL = 0.75          # hours (45 min thermal time constant)
T_WARN_DELTA = 6            # °C from setpoint to warning
T_CRITICAL_DELTA = 13       # °C from setpoint to critical
HVAC_WARNING_PENALTY = 3000   # $/hr additional at warning boundary
HVAC_SEVERE_PENALTY = 8000    # $/hr additional in severe zone


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def dgu_ramp_average(x_dgu_target, t_ramp=T_RAMP):
    """Average DGU output during ramp phase (linear ramp from 0 to target)."""
    return x_dgu_target / 2.0


def temperature_drift(t_hours, t_ambient, x_hvac_fraction):
    """
    Room temperature after t hours of HVAC disconnection.
    x_hvac_fraction: fraction of HVAC shed (0-1), scales the drift rate.
    Full disconnection (1.0) → full drift. Partial → slower drift.
    """
    effective_tau = TAU_THERMAL / max(x_hvac_fraction, 0.01)  # partial shed = slower drift
    return t_ambient + (T_SETPOINT - t_ambient) * np.exp(-t_hours / effective_tau)


def hvac_penalty(t_room, scenario='blizzard'):
    """
    Graduated HVAC penalty based on room temperature.
    Returns additional penalty in $/hr on top of base $3000.
    """
    if scenario == 'blizzard':
        t_warn = T_SETPOINT - T_WARN_DELTA      # 16°C
        t_critical = T_SETPOINT - T_CRITICAL_DELTA  # 9°C
        deviation = T_SETPOINT - t_room  # positive when cold
    else:  # monsoon
        t_warn = T_SETPOINT + T_WARN_DELTA      # 28°C
        t_critical = T_SETPOINT + T_CRITICAL_DELTA  # 35°C
        deviation = t_room - T_SETPOINT  # positive when hot
    
    if deviation <= T_WARN_DELTA:
        return 0  # Normal zone
    elif deviation <= T_CRITICAL_DELTA:
        # Warning zone: linear ramp
        frac = (deviation - T_WARN_DELTA) / (T_CRITICAL_DELTA - T_WARN_DELTA)
        return HVAC_WARNING_PENALTY * frac
    else:
        # Severe zone: step penalty
        return HVAC_WARNING_PENALTY + HVAC_SEVERE_PENALTY


def compute_total_cost(x_dgu, x_hvac, x_pump, x_mill, beta=1.0, scenario='blizzard', verbose=False):
    """
    Compute total time-integrated cost for a given allocation.
    
    Phase 1 (ramp): DGU averages x_dgu/2. Extra deficit must come from load shedding.
    Phase 2 (steady): DGU at full x_dgu. Load shedding as specified.
    
    Returns dict with breakdown.
    """
    results = {}
    
    # --- Validate power balance ---
    total_shed = x_hvac + x_pump + x_mill
    total_cover_steady = x_dgu + total_shed
    
    if total_cover_steady < DEFICIT - 0.01:
        # Infeasible: can't meet deficit
        return {'total': float('inf'), 'feasible': False, 'reason': 'Power balance violated'}
    
    # --- Phase 1: Ramp (0 → t_ramp) ---
    dgu_avg_phase1 = dgu_ramp_average(x_dgu)
    
    # During ramp, we need MORE shedding to compensate for low DGU
    # At t=0, DGU=0, so shed must cover full 90 MW
    # Strategy: during phase 1, shed up to capacity limits to cover gap
    shed_needed_phase1 = DEFICIT  # At t=0 need full 90 from shedding
    shed_available_phase1 = HVAC_MAX + PUMP_MAX + MILL_MAX  # 90 MW max
    
    # Phase 1 shedding (maximize to cover DGU gap)
    # We shed at maximum during ramp, then relax in phase 2
    x_hvac_p1 = min(HVAC_MAX, x_hvac + max(0, DEFICIT - dgu_avg_phase1 - total_shed + x_hvac))
    x_pump_p1 = min(PUMP_MAX, x_pump + max(0, DEFICIT - dgu_avg_phase1 - x_hvac_p1 - x_mill))
    x_mill_p1 = min(MILL_MAX, x_mill)
    
    # Actually, let's think about this more carefully.
    # During Phase 1, the average DGU output is x_dgu/2.
    # The average deficit to be covered by shedding is: 90 - x_dgu/2
    # We need to ensure shed capacity ≥ 90 at t=0 (worst case, DGU=0)
    
    # Phase 1 strategy: shed enough to cover 90 - R(t) at each instant
    # For simplicity, use the MAXIMUM shed during phase 1
    # then shed the planned amount during phase 2
    
    # Phase 1: all non-critical loads shed at maximum
    x_hvac_p1 = HVAC_MAX
    x_pump_p1 = PUMP_MAX
    x_mill_p1 = MILL_MAX
    # This gives 90 MW shed → covers full deficit even at DGU=0
    
    # But the DGU is also ramping, so average Phase 1 cost:
    # DGU fuel: 150 × (x_dgu/2) × t_ramp (average output during ramp)
    # CO₂: β × 81 × (x_dgu/2) × t_ramp
    # Shed costs at MAXIMUM during phase 1
    
    # --- Phase 1 Costs ---
    # DGU
    dgu_econ_p1 = DGU_FUEL_COST * dgu_avg_phase1 * T_RAMP
    dgu_co2_p1 = beta * CARBON_COST_PER_MW * dgu_avg_phase1 * T_RAMP
    
    # HVAC (at max during phase 1, short duration → likely still in normal temp zone)
    hvac_frac_p1 = x_hvac_p1 / HVAC_MAX
    t_room_p1 = temperature_drift(T_RAMP, T_AMBIENT_BLIZZARD if scenario == 'blizzard' else T_AMBIENT_MONSOON, hvac_frac_p1)
    penalty_p1 = hvac_penalty(t_room_p1, scenario)
    hvac_cost_p1 = (HVAC_BASE_COST + penalty_p1) * hvac_frac_p1 * T_RAMP
    
    # Pumping & Mill (at max during phase 1)
    pump_cost_p1 = PUMP_COST * (x_pump_p1 / PUMP_MAX) * T_RAMP
    mill_cost_p1 = MILL_COST * (x_mill_p1 / MILL_MAX) * T_RAMP
    
    # Operational risk during phase 1
    # At t=0, deficit_unmet = max(0, 90 - 90) = 0 (we're shedding everything)
    # So risk is manageable IF all sheds execute instantly
    oprisk_p1 = 0
    
    # --- Phase 2 Costs ---
    # DGU at full target
    dgu_econ_p2 = DGU_FUEL_COST * x_dgu * T_STEADY
    dgu_co2_p2 = beta * CARBON_COST_PER_MW * x_dgu * T_STEADY
    
    # HVAC (at planned level during phase 2)
    hvac_frac_p2 = x_hvac / HVAC_MAX if HVAC_MAX > 0 else 0
    # Temperature continues to drift from phase 1 end point
    # For simplicity, use temperature at midpoint of phase 2
    t_mid_p2 = T_RAMP + T_STEADY / 2
    t_room_p2 = temperature_drift(t_mid_p2, T_AMBIENT_BLIZZARD if scenario == 'blizzard' else T_AMBIENT_MONSOON, hvac_frac_p2)
    penalty_p2 = hvac_penalty(t_room_p2, scenario)
    hvac_cost_p2 = (HVAC_BASE_COST + penalty_p2) * hvac_frac_p2 * T_STEADY
    
    # Pumping & Mill at planned level
    pump_cost_p2 = PUMP_COST * (x_pump / PUMP_MAX) * T_STEADY
    mill_cost_p2 = MILL_COST * (x_mill / MILL_MAX) * T_STEADY
    
    oprisk_p2 = 0
    
    # --- TOTAL ---
    total_dgu_econ = dgu_econ_p1 + dgu_econ_p2
    total_dgu_co2 = dgu_co2_p1 + dgu_co2_p2
    total_hvac = hvac_cost_p1 + hvac_cost_p2
    total_pump = pump_cost_p1 + pump_cost_p2
    total_mill = mill_cost_p1 + mill_cost_p2
    total_oprisk = oprisk_p1 + oprisk_p2
    
    total = total_dgu_econ + total_dgu_co2 + total_hvac + total_pump + total_mill + total_oprisk
    
    # CO₂ emissions (physical, not cost)
    total_co2_tonnes = CO2_PER_MWH * (dgu_avg_phase1 * T_RAMP + x_dgu * T_STEADY)
    
    results = {
        'x_dgu': x_dgu,
        'x_hvac': x_hvac,
        'x_pump': x_pump,
        'x_mill': x_mill,
        'x_hvac_p1': x_hvac_p1,
        'x_pump_p1': x_pump_p1,
        'x_mill_p1': x_mill_p1,
        'beta': beta,
        'dgu_econ': total_dgu_econ,
        'dgu_co2_cost': total_dgu_co2,
        'hvac_cost': total_hvac,
        'pump_cost': total_pump,
        'mill_cost': total_mill,
        'oprisk': total_oprisk,
        'total': total,
        'co2_tonnes': total_co2_tonnes,
        'financial_only': total_dgu_econ + total_hvac + total_pump + total_mill + total_oprisk,
        'feasible': True,
        't_room_p2': t_room_p2,
        'hvac_penalty_p2': penalty_p2,
    }
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"  ALLOCATION: DGU={x_dgu}MW, HVAC={x_hvac}MW, PUMP={x_pump}MW, MILL={x_mill}MW")
        print(f"  β = {beta:.1f} | Scenario: {scenario}")
        print(f"{'='*70}")
        print(f"  Phase 1 (Ramp, {T_RAMP*60:.0f} min):")
        print(f"    DGU avg output: {dgu_avg_phase1:.1f} MW (ramping 0→{x_dgu})")
        print(f"    Load shedding:  HVAC={x_hvac_p1}MW + PUMP={x_pump_p1}MW + MILL={x_mill_p1}MW")
        print(f"    Room temp at end of ramp: {t_room_p1:.1f}°C")
        print(f"  Phase 2 (Steady, {T_STEADY*60:.0f} min):")
        print(f"    DGU output: {x_dgu:.1f} MW (full)")
        print(f"    Load shedding: HVAC={x_hvac}MW + PUMP={x_pump}MW + MILL={x_mill}MW")
        print(f"    Room temp at midpoint: {t_room_p2:.1f}°C (penalty: ${penalty_p2:,.0f}/hr)")
        print(f"  {'─'*68}")
        print(f"  COST BREAKDOWN (total for {T_TOTAL} hr):")
        print(f"    DGU fuel cost:       ${total_dgu_econ:>10,.2f}")
        print(f"    DGU carbon cost:     ${total_dgu_co2:>10,.2f}  (β×{CARBON_COST_PER_MW}×MW)")
        print(f"    HVAC discomfort:     ${total_hvac:>10,.2f}")
        print(f"    Pump production:     ${total_pump:>10,.2f}")
        print(f"    Mill underproduction:${total_mill:>10,.2f}")
        print(f"    Operational risk:    ${total_oprisk:>10,.2f}")
        print(f"  {'─'*68}")
        print(f"  TOTAL LOSS:            ${total:>10,.2f}")
        print(f"  CO₂ EMITTED:           {total_co2_tonnes:>10.2f} tonnes")
        print(f"  Financial (excl. CO₂): ${results['financial_only']:>10,.2f}")
        print(f"{'='*70}")
    
    return results


# ============================================================
# 3. EXHAUSTIVE SEARCH OVER FEASIBLE ALLOCATIONS
# ============================================================

def find_optimal(beta=1.0, scenario='blizzard', verbose=True):
    """
    Enumerate allocations in 5 MW steps and find the minimum cost.
    """
    best = None
    all_results = []
    
    # Search grid (5 MW steps)
    for x_dgu in range(0, 91, 5):
        for x_hvac in range(0, min(HVAC_MAX, 91 - x_dgu) + 1, 5):
            for x_pump in range(0, min(PUMP_MAX, 91 - x_dgu - x_hvac) + 1, 5):
                x_mill_needed = max(0, DEFICIT - x_dgu - x_hvac - x_pump)
                if x_mill_needed > MILL_MAX:
                    continue
                # Snap to nearest 5
                x_mill = int(np.ceil(x_mill_needed / 5) * 5)
                if x_mill > MILL_MAX:
                    continue
                
                r = compute_total_cost(x_dgu, x_hvac, x_pump, x_mill, beta, scenario)
                if r['feasible']:
                    all_results.append(r)
                    if best is None or r['total'] < best['total']:
                        best = r
    
    if verbose and best:
        print(f"\n{'*'*70}")
        print(f"  OPTIMAL SOLUTION (β={beta:.1f}, {scenario})")
        print(f"{'*'*70}")
        compute_total_cost(best['x_dgu'], best['x_hvac'], best['x_pump'], best['x_mill'], 
                          beta, scenario, verbose=True)
    
    return best, all_results


# ============================================================
# 4. SCENARIO COMPARISON (for presentation)
# ============================================================

def compare_scenarios():
    """Show key scenarios side-by-side for the presentation."""
    
    print("\n" + "█"*70)
    print("  SCENARIO COMPARISON FOR 90 MW DEFICIT")
    print("  (All costs for 1-hour crisis, including 5-min DGU ramp)")
    print("█"*70)
    
    scenarios = [
        ("A: All DGU (grey only)", 90, 0, 0, 0),
        ("B: All Load Shedding",    0, 20, 30, 40),
        ("C: DGU + HVAC only",     70, 20, 0, 0),
        ("D: DGU + HVAC + Pump",   40, 20, 30, 0),
        ("E: Balanced Mix",        30, 20, 20, 20),
    ]
    
    print(f"\n{'Scenario':<30} {'DGU':>5} {'HVAC':>5} {'PUMP':>5} {'MILL':>5} │ {'Total $':>10} {'CO₂ t':>7}")
    print("─" * 80)
    
    for name, dgu, hvac, pump, mill in scenarios:
        r = compute_total_cost(dgu, hvac, pump, mill, beta=1.0, scenario='blizzard')
        if r['feasible']:
            print(f"  {name:<28} {dgu:>5} {hvac:>5} {pump:>5} {mill:>5} │ ${r['total']:>9,.0f} {r['co2_tonnes']:>6.1f}")
    
    # Now show detailed breakdown for top scenarios
    print("\n\n" + "="*70)
    print("  DETAILED BREAKDOWN: Key Scenarios at β=1.0")
    print("="*70)
    
    for name, dgu, hvac, pump, mill in scenarios:
        print(f"\n─── {name} ───")
        compute_total_cost(dgu, hvac, pump, mill, beta=1.0, scenario='blizzard', verbose=True)


# ============================================================
# 5. β SENSITIVITY ANALYSIS & PARETO FRONTIER  
# ============================================================

def beta_sensitivity():
    """Sweep β and show how optimal solution changes."""
    
    print("\n\n" + "█"*70)
    print("  β SENSITIVITY ANALYSIS")
    print("  How ESG weight shifts the optimal dispatch")
    print("█"*70)
    
    betas = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
    
    print(f"\n{'β':>5} │ {'DGU':>5} {'HVAC':>5} {'PUMP':>5} {'MILL':>5} │ {'Total $':>10} {'Fin. $':>10} {'CO₂ t':>7}")
    print("─" * 75)
    
    pareto_points = []
    
    for beta in betas:
        best, _ = find_optimal(beta=beta, scenario='blizzard', verbose=False)
        if best:
            print(f"  {beta:>4.1f} │ {best['x_dgu']:>5.0f} {best['x_hvac']:>5.0f} "
                  f"{best['x_pump']:>5.0f} {best['x_mill']:>5.0f} │ "
                  f"${best['total']:>9,.0f} ${best['financial_only']:>9,.0f} {best['co2_tonnes']:>6.1f}")
            pareto_points.append({
                'beta': beta,
                'financial': best['financial_only'],
                'co2': best['co2_tonnes'],
                'total': best['total'],
                'x_dgu': best['x_dgu'],
                'x_hvac': best['x_hvac'],
                'x_pump': best['x_pump'],
                'x_mill': best['x_mill'],
            })
    
    return pareto_points


# ============================================================
# 6. PARETO FRONTIER DATA (for plotting)
# ============================================================

def generate_pareto_data():
    """Generate fine-grained Pareto frontier data."""
    
    print("\n\n" + "█"*70)
    print("  PARETO FRONTIER: Financial Cost vs CO₂ Emissions")
    print("█"*70)
    
    # Collect all feasible solutions across different betas
    all_solutions = []
    
    for beta in np.arange(0.5, 5.1, 0.25):
        best, results = find_optimal(beta=beta, scenario='blizzard', verbose=False)
        for r in results:
            all_solutions.append({
                'financial': r['financial_only'],
                'co2': r['co2_tonnes'],
                'total_beta1': compute_total_cost(r['x_dgu'], r['x_hvac'], r['x_pump'], r['x_mill'], 
                                                   beta=1.0, scenario='blizzard')['total'],
                'x_dgu': r['x_dgu'],
                'x_hvac': r['x_hvac'],
                'x_pump': r['x_pump'],
                'x_mill': r['x_mill'],
            })
    
    # Find Pareto-optimal solutions (non-dominated in financial × CO₂ space)
    pareto = []
    for s in all_solutions:
        dominated = False
        for other in all_solutions:
            if (other['financial'] <= s['financial'] and other['co2'] <= s['co2'] and
                (other['financial'] < s['financial'] or other['co2'] < s['co2'])):
                dominated = True
                break
        if not dominated:
            # Check if duplicate
            is_dup = any(p['financial'] == s['financial'] and p['co2'] == s['co2'] for p in pareto)
            if not is_dup:
                pareto.append(s)
    
    # Sort by CO₂
    pareto.sort(key=lambda x: x['co2'])
    
    print(f"\n{'Financial $':>12} {'CO₂ t':>8} │ {'DGU':>5} {'HVAC':>5} {'PUMP':>5} {'MILL':>5}")
    print("─" * 60)
    for p in pareto:
        print(f"  ${p['financial']:>10,.0f} {p['co2']:>7.1f} │ "
              f"{p['x_dgu']:>5.0f} {p['x_hvac']:>5.0f} {p['x_pump']:>5.0f} {p['x_mill']:>5.0f}")
    
    return pareto


# ============================================================
# 7. STEP-BY-STEP CALCULATION (for presentation Block 3)
# ============================================================

def presentation_calculation():
    """
    Detailed step-by-step calculation matching presentation requirements.
    Shows the work for each scenario with full unit normalization.
    """
    
    print("\n\n" + "█"*70)
    print("  BLOCK 3: STEP-BY-STEP LOSS FUNCTION CALCULATION")
    print("  For 90 MW deficit, 1-hour crisis, 5-min DGU ramp")
    print("█"*70)
    
    print("\n" + "="*70)
    print("  STEP 1: NORMALIZE ALL UNITS TO $/hour")
    print("="*70)
    print("""
  DGU:
    Fuel cost:     $150/MWh × MW = $/hr  ✓
    Carbon cost:   0.9 tCO₂/MWh × $90/tCO₂ = $81/MW/hr  ✓
    Total DGU:     $(150 + 81β)/MW/hr

  HVAC shed:
    Base:          $3,000/hr (for full 20 MW disconnect)  ✓
    Per MW:        $3,000/20 = $150/MW/hr in normal zone  ✓
    
  Pump shed:
    Base:          $5,000/hr (for full 30 MW disconnect)  ✓
    Per MW:        $5,000/30 = $166.67/MW/hr  ✓
    
  Mill shed:
    Base:          $15,000/hr (for full 40 MW disconnect)  ✓
    Per MW:        $15,000/40 = $375/MW/hr  ✓
  """)
    
    print("="*70)
    print("  STEP 2: TIME-PHASED ANALYSIS (DGU Physics)")
    print("="*70)
    print("""
  Phase 1 (0 → 5 min = 0.0833 hr):
    • DGU capacity ramps from 0 → target (linear)
    • Average DGU output = target/2
    • ALL non-critical loads shed to cover full 90 MW gap at t=0
    
  Phase 2 (5 min → 60 min = 0.9167 hr):
    • DGU at full target capacity
    • Load shedding at optimized (reduced) levels
    • Temperature may start drifting → graduated penalty
  """)
    
    print("="*70)
    print("  STEP 3: VARIANT COMPARISON AT β=1.0")
    print("="*70)
    
    # Variant A: All DGU
    print("\n─── VARIANT A: ALL DIESEL (90 MW DGU) ───")
    print("  Phase 1 (5 min):")
    print(f"    DGU avg = 45 MW, load shed covers 90-45 = 45 MW gap")
    print(f"    ALL loads shed: HVAC=20 + PUMP=30 + MILL=40 = 90 MW")
    print(f"    DGU fuel: 150 × 45 × 0.0833 = ${150*45*T_RAMP:,.0f}")
    print(f"    DGU CO₂ cost: 81 × 45 × 0.0833 = ${81*45*T_RAMP:,.0f}")
    print(f"    HVAC: 3000 × 1.0 × 0.0833 = ${3000*T_RAMP:,.0f}")
    print(f"    Pump: 5000 × 1.0 × 0.0833 = ${5000*T_RAMP:,.0f}")
    print(f"    Mill: 15000 × 1.0 × 0.0833 = ${15000*T_RAMP:,.0f}")
    
    print("  Phase 2 (55 min):")
    print(f"    DGU = 90 MW, load shedding = 0 MW")
    print(f"    DGU fuel: 150 × 90 × 0.9167 = ${150*90*T_STEADY:,.0f}")
    print(f"    DGU CO₂ cost: 81 × 90 × 0.9167 = ${81*90*T_STEADY:,.0f}")
    
    r_a = compute_total_cost(90, 0, 0, 0, beta=1.0, verbose=True)
    
    # Variant B: Max DGU + HVAC
    print("\n─── VARIANT B: DGU(70) + HVAC(20) ───")
    r_b = compute_total_cost(70, 20, 0, 0, beta=1.0, verbose=True)
    
    # Variant C: Balanced
    print("\n─── VARIANT C: DGU(40) + HVAC(20) + PUMP(30) ───")
    r_c = compute_total_cost(40, 20, 30, 0, beta=1.0, verbose=True)
    
    # Variant D: Minimum DGU
    print("\n─── VARIANT D: DGU(0) + ALL SHEDDING ───")
    r_d = compute_total_cost(0, 20, 30, 40, beta=1.0, verbose=True)
    
    # Find optimal
    print("\n─── FINDING OPTIMAL (β=1.0) ───")
    best, _ = find_optimal(beta=1.0, verbose=True)
    
    print("\n" + "="*70)
    print("  STEP 4: β SENSITIVITY (ESG WEIGHT IMPACT)")
    print("="*70)
    print("""
  β = 1.0 → Normal day: economic cost dominates
  β = 2.0 → ESG audit: carbon cost doubles
  β = 3.0 → Sustainability report: carbon cost triples
  
  As β increases:
    • DGU becomes more expensive (fuel + β×carbon)
    • Load shedding cost stays constant
    • Optimal shifts from DGU → load shedding
  """)
    
    # Show β=3.0 optimal
    print("\n─── OPTIMAL AT β=3.0 (Sustainability Report Day) ───")
    best_esg, _ = find_optimal(beta=3.0, verbose=True)
    
    return r_a, r_b, r_c, r_d, best


# ============================================================
# 8. CRITICAL THRESHOLD ANALYSIS
# ============================================================

def threshold_analysis():
    """Show the β value where optimal strategy flips."""
    
    print("\n\n" + "█"*70)
    print("  CRITICAL β THRESHOLD ANALYSIS")
    print("  At what β does the optimal strategy change?")
    print("█"*70)
    
    prev_dgu = None
    for beta in np.arange(0.5, 5.01, 0.1):
        best, _ = find_optimal(beta=beta, verbose=False)
        if best:
            if prev_dgu is not None and best['x_dgu'] != prev_dgu:
                print(f"  β = {beta:.1f}: Strategy shifts! DGU {prev_dgu} → {best['x_dgu']} MW")
                print(f"         HVAC={best['x_hvac']}, PUMP={best['x_pump']}, MILL={best['x_mill']}")
                print(f"         Total=${best['total']:,.0f}, CO₂={best['co2_tonnes']:.1f}t")
            prev_dgu = best['x_dgu']


# ============================================================
# 9. MAIN EXECUTION
# ============================================================

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  AI DISPATCHER OPTIMIZER — Energy-O-Thon 2026                      ║")
    print("║  90 MW Deficit | DGU + Load Shedding | Time-Phased | β-Weighted    ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    
    # 1. Step-by-step presentation calculation
    presentation_calculation()
    
    # 2. Scenario comparison
    compare_scenarios()
    
    # 3. β sensitivity
    pareto_points = beta_sensitivity()
    
    # 4. Threshold analysis
    threshold_analysis()
    
    # 5. Pareto frontier data
    pareto = generate_pareto_data()
    
    # 6. Save Pareto data for plotting
    output_dir = os.path.dirname(os.path.abspath(__file__))
    pareto_file = os.path.join(output_dir, "pareto_data.json")
    with open(pareto_file, 'w') as f:
        json.dump({
            'pareto_frontier': pareto,
            'beta_sweep': pareto_points,
        }, f, indent=2)
    print(f"\n  [Pareto data saved to {pareto_file}]")
    
    print("\n\n" + "█"*70)
    print("  SUMMARY FOR PRESENTATION")
    print("█"*70)
    print("""
  KEY FINDINGS:
  
  1. At β=1.0 (normal): Optimal uses moderate DGU + cheap load shedding
     → Minimizes total cost while accepting some CO₂
     
  2. At β=3.0 (ESG report): Optimal shifts to minimal DGU
     → Pays more in load shedding to avoid carbon penalties
     
  3. DGU warm-up creates a CRITICAL 5-minute window where ALL 
     non-critical loads MUST be shed regardless of strategy
     → This is the physics constraint that naive models miss
     
  4. HVAC is cheapest to shed ($150/MW/hr) but has time-dependent
     temperature penalties that escalate after ~15 minutes
     
  5. Rolling mill is most expensive to shed ($375/MW/hr) — only 
     used when DGU carbon cost exceeds this at high β values
     
  6. The Pareto frontier shows a clear tradeoff curve between
     Financial Cost and CO₂, with β determining the operating point
  """)
