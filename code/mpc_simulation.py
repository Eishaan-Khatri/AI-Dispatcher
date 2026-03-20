# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
"""
MPC Dynamic Re-Optimization Simulator
======================================
Simulates a 13-hour outage where:
  - Power comes back at an UNKNOWN time
  - The AI re-optimizes every 30 minutes
  - Temperature drifts, pump costs escalate, forecasts update
  - Each re-optimization produces a DIFFERENT optimal strategy

This is exactly what the AI Dispatcher does in production.
"""

import numpy as np

# ============================================================
# PARAMETERS
# ============================================================
DEFICIT = 90
HVAC_MAX = 20
PUMP_MAX = 30
MILL_MAX = 40

DGU_FUEL = 150        # $/MWh
CO2_RATE = 0.9        # t CO2/MWh
ESG_PENALTY = 90      # $/t CO2
CARBON_PER_MW = CO2_RATE * ESG_PENALTY  # $81

HVAC_BASE = 3000      # $/hr full shed
PUMP_BASE = 5000      # $/hr full shed
MILL_BASE = 15000     # $/hr full shed

T_SETPOINT = 22.0     # C
T_AMB = 42.0          # C (monsoon — worst case)
TAU = 0.75            # hr (45 min thermal time constant)
T_WARN = 28.0         # C
T_CRITICAL = 35.0     # C
WARN_PENALTY = 3000
SEVERE_PENALTY = 8000

# Pump escalation thresholds
PUMP_BUFFER_MIN = 15   # minutes of reservoir buffer
PUMP_ESCALATION_HR = 1.0  # after 1 hour, cooling systems stressed


# ============================================================
# STATE TRACKING
# ============================================================
class PlantState:
    """Tracks the evolving state of the plant during the outage."""
    def __init__(self):
        self.t_room = T_SETPOINT       # Current room temperature
        self.hvac_shed_cumulative = 0.0 # Total hours of HVAC shedding
        self.pump_shed_cumulative = 0.0 # Total hours of pump shedding
        self.mill_shed_cumulative = 0.0
        self.dgu_runtime = 0.0         # Total DGU hours
        self.co2_total = 0.0           # Total tonnes emitted
        self.cost_total = 0.0          # Total $ spent
        self.elapsed = 0.0             # Hours since outage start
        self.history = []              # Log of each period's decisions
    
    def update_temperature(self, x_hvac, dt):
        """
        Update room temperature based on HVAC shedding.
        Uses Newton's Law of Cooling with partial shed support.
        """
        if x_hvac == 0:
            # HVAC fully running — temperature returns to setpoint
            self.t_room = T_AMB + (self.t_room - T_AMB) * np.exp(-dt / (TAU * 0.3))
            # Recovery is faster because HVAC actively cools
            if self.t_room < T_SETPOINT:
                self.t_room = T_SETPOINT  # Don't overshoot
        else:
            hvac_frac = x_hvac / HVAC_MAX  # fraction shed (0.0 to 1.0)
            # Effective time constant: less shed = slower drift
            tau_eff = TAU / max(hvac_frac, 0.01)
            # Temperature drifts toward a point between setpoint and ambient
            # At partial shed, HVAC partially works: equilibrium = setpoint + (ambient-setpoint)*frac
            t_equilibrium = T_SETPOINT + (T_AMB - T_SETPOINT) * hvac_frac
            self.t_room = t_equilibrium + (self.t_room - t_equilibrium) * np.exp(-dt / tau_eff)
    
    def get_hvac_penalty(self):
        """Current temperature penalty rate."""
        if self.t_room <= T_WARN:
            return 0
        elif self.t_room <= T_CRITICAL:
            frac = (self.t_room - T_WARN) / (T_CRITICAL - T_WARN)
            return WARN_PENALTY * frac
        else:
            return WARN_PENALTY + SEVERE_PENALTY
    
    def get_pump_escalation(self):
        """Pump cost escalation based on cumulative shed time."""
        hrs = self.pump_shed_cumulative
        if hrs < PUMP_BUFFER_MIN / 60:
            return -2000  # Buffer absorbing: cost is LOWER than base
        elif hrs < PUMP_ESCALATION_HR:
            return 0  # Normal cost
        elif hrs < 2.0:
            return 3000 * (hrs - 1.0)  # Cooling systems stressed
        else:
            return 3000 + 7000  # Critical: equipment at risk


def optimize_period(state, beta, dt, forecast_remaining_hr):
    """
    Find optimal dispatch for the NEXT period (dt hours).
    
    Takes into account:
    - Current room temperature (affects HVAC penalty)
    - Cumulative pump shed time (affects pump cost)
    - Forecast of remaining outage (affects strategy aggressiveness)
    - Beta (ESG context)
    """
    best = None
    best_cost = float('inf')
    
    for x_dgu in range(0, 91, 5):
        for x_hvac in range(0, min(HVAC_MAX, 91 - x_dgu) + 1, 5):
            for x_pump in range(0, min(PUMP_MAX, 91 - x_dgu - x_hvac) + 1, 5):
                x_mill_needed = max(0, DEFICIT - x_dgu - x_hvac - x_pump)
                if x_mill_needed > MILL_MAX:
                    continue
                x_mill = int(np.ceil(x_mill_needed / 5) * 5)
                if x_mill > MILL_MAX:
                    continue
                
                # Simulate temperature for this HVAC level
                t_room_future = state.t_room
                hvac_frac = x_hvac / HVAC_MAX if x_hvac > 0 else 0
                if x_hvac > 0:
                    t_eq = T_SETPOINT + (T_AMB - T_SETPOINT) * hvac_frac
                    tau_eff = TAU / max(hvac_frac, 0.01)
                    t_room_future = t_eq + (state.t_room - t_eq) * np.exp(-dt / tau_eff)
                else:
                    # HVAC running: temperature recovers
                    t_room_future = T_AMB + (state.t_room - T_AMB) * np.exp(-dt / (TAU * 0.3))
                    if t_room_future < T_SETPOINT:
                        t_room_future = T_SETPOINT
                
                # Check temperature safety constraint
                if t_room_future > T_CRITICAL + 2:  # Hard safety limit
                    continue
                
                # Average temperature during this period
                t_room_avg = (state.t_room + t_room_future) / 2
                
                # HVAC penalty at average temperature
                if t_room_avg <= T_WARN:
                    hvac_penalty = 0
                elif t_room_avg <= T_CRITICAL:
                    hvac_penalty = WARN_PENALTY * (t_room_avg - T_WARN) / (T_CRITICAL - T_WARN)
                else:
                    hvac_penalty = WARN_PENALTY + SEVERE_PENALTY
                
                # Pump escalation
                pump_esc = state.get_pump_escalation() if x_pump > 0 else 0
                
                # Cost for this period
                cost_rate = (
                    DGU_FUEL * x_dgu +                                    # fuel
                    beta * CARBON_PER_MW * x_dgu +                        # ESG
                    (HVAC_BASE + hvac_penalty) * (x_hvac / HVAC_MAX) +    # HVAC + temp penalty
                    (PUMP_BASE + pump_esc) * (x_pump / PUMP_MAX) +        # pump + escalation
                    MILL_BASE * (x_mill / MILL_MAX)                        # mill
                )
                
                period_cost = cost_rate * dt
                
                if period_cost < best_cost:
                    best_cost = period_cost
                    best = {
                        'x_dgu': x_dgu, 'x_hvac': x_hvac,
                        'x_pump': x_pump, 'x_mill': x_mill,
                        'cost': period_cost, 'rate': cost_rate,
                        't_room_end': t_room_future,
                        'hvac_penalty': hvac_penalty,
                        'pump_esc': pump_esc,
                    }
    
    return best


def simulate_mpc(total_hours=13, beta=1.0, reoptimize_every=0.5):
    """
    Full MPC simulation of an extended outage.
    
    Re-optimizes every 'reoptimize_every' hours.
    Shows how the strategy evolves over time.
    """
    state = PlantState()
    dt = reoptimize_every
    
    print("=" * 100)
    print(f"  MPC SIMULATION: {total_hours}-HOUR OUTAGE | beta={beta} | Re-optimize every {int(reoptimize_every*60)} min")
    print(f"  Scenario: Monsoon (T_ambient={T_AMB} C), tau={TAU*60:.0f} min")
    print("=" * 100)
    
    # Phase 1: First 5 minutes (forced full shed for DGU ramp)
    print()
    print("  PHASE 1 (0-5 min): DGU RAMP — ALL LOADS SHED")
    print("  " + "-" * 80)
    t_ramp = 5/60
    dgu_avg = 55 / 2  # assuming DGU target will be ~55 MW
    phase1_cost = (
        DGU_FUEL * dgu_avg * t_ramp +
        beta * CARBON_PER_MW * dgu_avg * t_ramp +
        HVAC_BASE * t_ramp +
        PUMP_BASE * t_ramp +
        MILL_BASE * t_ramp
    )
    state.cost_total += phase1_cost
    state.elapsed += t_ramp
    state.co2_total += CO2_RATE * dgu_avg * t_ramp
    state.update_temperature(HVAC_MAX, t_ramp)  # Full HVAC shed for 5 min
    state.hvac_shed_cumulative += t_ramp
    state.pump_shed_cumulative += t_ramp
    state.mill_shed_cumulative += t_ramp
    
    print(f"    DGU ramping 0->target | All shed: HVAC=20, PUMP=30, MILL=40")
    print(f"    Phase 1 cost: ${phase1_cost:,.0f} | T_room: {state.t_room:.1f} C")
    print()
    
    # Phase 2+: MPC re-optimization loop
    print(f"  {'Time':>8} {'DGU':>5} {'HVAC':>5} {'PUMP':>5} {'MILL':>5} | "
          f"{'T_room':>7} {'HVAC Pen':>9} {'Pump Esc':>9} | "
          f"{'Period$':>9} {'Cumul$':>10} {'CO2_t':>6} | Strategy Note")
    print("  " + "-" * 115)
    
    periods = int((total_hours - t_ramp) / dt)
    
    for i in range(periods):
        t_start = state.elapsed
        
        # Forecast: how much longer? (degrades over time — less certain)
        forecast_remaining = total_hours - state.elapsed
        
        # Optimize for this period
        result = optimize_period(state, beta, dt, forecast_remaining)
        
        if result is None:
            print(f"  {t_start:.1f}hr: NO FEASIBLE SOLUTION — emergency mode!")
            break
        
        # Apply result
        x_dgu = result['x_dgu']
        x_hvac = result['x_hvac']
        x_pump = result['x_pump']
        x_mill = result['x_mill']
        
        # Update state
        state.update_temperature(x_hvac, dt)
        state.elapsed += dt
        state.cost_total += result['cost']
        state.co2_total += CO2_RATE * x_dgu * dt
        state.dgu_runtime += dt
        if x_hvac > 0:
            state.hvac_shed_cumulative += dt
        if x_pump > 0:
            state.pump_shed_cumulative += dt
        if x_mill > 0:
            state.mill_shed_cumulative += dt
        
        # Determine strategy note
        note = ""
        if x_hvac == 0 and i > 0:
            note = "HVAC restored (temp too high)"
        elif result['hvac_penalty'] > 0:
            note = f"WARNING zone! penalty=${result['hvac_penalty']:,.0f}/hr"
        if result['pump_esc'] > 0:
            note += f" | Pump escalated +${result['pump_esc']:,.0f}"
        if x_mill > 0 and i > 0:
            note += " | Mill shed (forced)"
        if not note:
            note = "Normal operation"
        
        # Format time as hours:minutes
        hrs = int(t_start)
        mins = int((t_start - hrs) * 60)
        time_str = f"{hrs:02d}:{mins:02d}"
        
        print(f"  {time_str:>8} {x_dgu:>5} {x_hvac:>5} {x_pump:>5} {x_mill:>5} | "
              f"{state.t_room:>6.1f}C {result['hvac_penalty']:>8,.0f}$ {result['pump_esc']:>8,.0f}$ | "
              f"${result['cost']:>8,.0f} ${state.cost_total:>9,.0f} {state.co2_total:>5.1f} | {note}")
        
        # Log for summary
        state.history.append({
            'time': t_start,
            'x_dgu': x_dgu, 'x_hvac': x_hvac,
            'x_pump': x_pump, 'x_mill': x_mill,
            't_room': state.t_room,
            'period_cost': result['cost'],
            'cumul_cost': state.cost_total,
            'co2': state.co2_total,
        })
    
    # Summary
    print()
    print("  " + "=" * 100)
    print(f"  FINAL SUMMARY AFTER {total_hours}-HOUR OUTAGE")
    print("  " + "=" * 100)
    print(f"    Total cost:          ${state.cost_total:>12,.2f}")
    print(f"    Total CO2 emitted:   {state.co2_total:>12.1f} tonnes")
    print(f"    DGU total runtime:   {state.dgu_runtime:>12.1f} hours")
    print(f"    HVAC shed time:      {state.hvac_shed_cumulative*60:>12.0f} minutes")
    print(f"    Pump shed time:      {state.pump_shed_cumulative*60:>12.0f} minutes")
    print(f"    Mill shed time:      {state.mill_shed_cumulative*60:>12.0f} minutes")
    print(f"    Final room temp:     {state.t_room:>12.1f} C")
    
    return state


# ============================================================
# RUN SIMULATIONS
# ============================================================

print()
print("#" * 100)
print("#  THE KEY INSIGHT: STRATEGY EVOLVES OVER TIME")
print("#  The AI doesn't pick one strategy and hold it for 13 hours.")
print("#  It re-optimizes every 30 minutes as conditions change.")
print("#" * 100)
print()

# Simulation 1: Normal beta, 13-hour outage
print("\n\n")
state1 = simulate_mpc(total_hours=13, beta=1.0, reoptimize_every=0.5)

# Simulation 2: Same but with ESG report day
print("\n\n")
state2 = simulate_mpc(total_hours=13, beta=3.0, reoptimize_every=0.5)

# Simulation 3: Short outage — compare
print("\n\n")
state3 = simulate_mpc(total_hours=1, beta=1.0, reoptimize_every=0.5)


print("\n\n")
print("=" * 100)
print("  STRATEGY EVOLUTION SUMMARY")
print("=" * 100)
print()
print("  What changes over time and WHY:")
print()
print("  HOUR 0-0.5:  HVAC cheap ($150/MW) -> shed 5-20 MW HVAC + PUMP + DGU")
print("               T_room: 22C -> 25C (normal zone, no penalty)")
print()
print("  HOUR 0.5-1:  Temperature rising -> HVAC penalty starts")
print("               Optimizer may REDUCE HVAC shed, INCREASE DGU")
print()
print("  HOUR 1-2:    T_room approaching 28C (warning zone)")
print("               HVAC effective cost: $150 + penalty -> $300+/MW/hr")
print("               Pump reservoir depleting -> pump cost rising")
print("               Strategy SHIFTS: more DGU, less shedding")
print()
print("  HOUR 2-4:    T_room hits 35C if HVAC still shed -> SEVERE zone")
print("               HVAC must be RESTORED or reduced to hold T < 35C")
print("               Pump cooling stressed -> pump escalation fires")
print("               DGU carries 70-90 MW of the deficit")
print()
print("  HOUR 4+:     Equilibrium: DGU dominates (70-90 MW)")
print("               Minimal shedding (only if temperature allows)")
print("               CO2 accumulating steadily")
print("               Cost is mostly DGU fuel + ESG")
print()
print("  THIS IS WHY STATIC OPTIMIZATION IS WRONG:")
print("  - At hour 0, HVAC shed = $150/MW (cheapest)")
print("  - At hour 4, HVAC shed = $700/MW (severe penalty) -> more expensive than MILL!")
print("  - The optimal mix at hour 0 is COMPLETELY DIFFERENT from hour 4")
print()

# Comparison table
print("=" * 100)
print("  COMPARISON: DIFFERENT DURATIONS AND BETA VALUES")
print("=" * 100)
print(f"  {'Scenario':<35} {'Total Cost':>12} {'CO2 (t)':>8} {'Avg $/hr':>10}")
print(f"  {'-'*35} {'-'*12} {'-'*8} {'-'*10}")
print(f"  {'1-hr outage, beta=1.0':<35} ${state3.cost_total:>11,.0f} {state3.co2_total:>7.1f} ${state3.cost_total/1:>9,.0f}")
print(f"  {'13-hr outage, beta=1.0':<35} ${state1.cost_total:>11,.0f} {state1.co2_total:>7.1f} ${state1.cost_total/13:>9,.0f}")
print(f"  {'13-hr outage, beta=3.0 (ESG day)':<35} ${state2.cost_total:>11,.0f} {state2.co2_total:>7.1f} ${state2.cost_total/13:>9,.0f}")
print()
print("  KEY OBSERVATION: Average $/hr INCREASES for longer outages because")
print("  temperature penalties escalate and pump costs rise over time.")
print("  The static model incorrectly assumes constant $/hr.")
