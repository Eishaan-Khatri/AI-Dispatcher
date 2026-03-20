"""
Pareto Frontier Plotter — Energy-O-Thon 2026
Generates the Financial Cost vs CO₂ Emissions Pareto frontier
with β sweep annotations.
"""

import json
import os
import sys

# Try matplotlib, if not available, generate ASCII plot
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("[WARNING] matplotlib not found. Install with: pip install matplotlib")
    print("          Generating ASCII-only Pareto data instead.\n")

import numpy as np


def load_pareto_data(filepath):
    """Load Pareto data from the optimizer output."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data


def create_pareto_plot(data, output_path):
    """Create a publication-quality Pareto frontier plot."""
    
    pareto = data['pareto_frontier']
    beta_sweep = data['beta_sweep']
    
    # Extract coordinates
    pareto_fin = [p['financial'] for p in pareto]
    pareto_co2 = [p['co2'] for p in pareto]
    
    beta_fin = [b['financial'] for b in beta_sweep]
    beta_co2 = [b['co2'] for b in beta_sweep]
    beta_vals = [b['beta'] for b in beta_sweep]
    
    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    
    # Style
    fig.patch.set_facecolor('#1a1a2e')
    ax.set_facecolor('#16213e')
    
    # Plot Pareto frontier line
    ax.plot(pareto_fin, pareto_co2, 'o-', color='#00d4ff', linewidth=2.5,
            markersize=6, markerfacecolor='#00d4ff', markeredgecolor='white',
            markeredgewidth=0.8, alpha=0.9, label='Pareto Frontier', zorder=3)
    
    # Fill area under Pareto frontier (feasible region indicator)
    ax.fill_between(pareto_fin, pareto_co2, max(pareto_co2)*1.1, 
                     alpha=0.05, color='#00d4ff')
    
    # Highlight beta sweep optimal points
    colors_beta = plt.cm.plasma(np.linspace(0.2, 0.9, len(beta_sweep)))
    for i, (bf, bc, bv) in enumerate(zip(beta_fin, beta_co2, beta_vals)):
        ax.scatter(bf, bc, s=150, color=colors_beta[i], edgecolors='white',
                   linewidth=1.5, zorder=5, marker='D')
        # Annotate with beta value
        offset_x = 400 if i % 2 == 0 else -800
        offset_y = 2 if i % 2 == 0 else -3
        ax.annotate(f'β={bv:.1f}', (bf, bc), fontsize=10, fontweight='bold',
                   color='white', ha='center', va='bottom',
                   xytext=(offset_x, offset_y + 8),
                   textcoords='offset points',
                   arrowprops=dict(arrowstyle='->', color='#cccccc', lw=0.8),
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='#0a3d62', 
                            edgecolor='#00d4ff', alpha=0.8))
    
    # Mark key regions
    # "All DGU" region (high CO2, low cost)
    ax.annotate('ALL DGU\n(Cheapest, Dirtiest)', 
                xy=(min(pareto_fin), max(pareto_co2)),
                fontsize=9, color='#ff6b6b', fontstyle='italic',
                ha='left', va='top',
                xytext=(30, -10), textcoords='offset points')
    
    # "All Shedding" region (low CO2, high cost)  
    ax.annotate('ALL SHEDDING\n(Cleanest, Most Expensive)',
                xy=(max(pareto_fin), min(pareto_co2)),
                fontsize=9, color='#51cf66', fontstyle='italic',
                ha='right', va='bottom',
                xytext=(-30, 10), textcoords='offset points')
    
    # Labels and title
    ax.set_xlabel('Financial Cost ($/hour, excl. CO₂ penalty)', fontsize=13, 
                  color='white', fontweight='bold', labelpad=10)
    ax.set_ylabel('CO₂ Emissions (tonnes/hour)', fontsize=13,
                  color='white', fontweight='bold', labelpad=10)
    ax.set_title('Pareto Frontier: Financial Cost vs CO₂ Emissions\n'
                 '90 MW Deficit — β Sensitivity Analysis', 
                 fontsize=16, color='white', fontweight='bold', pad=20)
    
    # Grid
    ax.grid(True, alpha=0.15, color='white', linestyle='--')
    ax.tick_params(colors='white', labelsize=11)
    for spine in ax.spines.values():
        spine.set_color('#555555')
    
    # Legend
    legend_elements = [
        plt.Line2D([0], [0], marker='o', color='#00d4ff', linewidth=2,
                   markersize=8, markerfacecolor='#00d4ff', markeredgecolor='white',
                   label='Pareto-Optimal Solutions'),
        plt.Line2D([0], [0], marker='D', color='w', linewidth=0,
                   markersize=8, markerfacecolor='#e040fb',
                   label='β-Optimal Points'),
    ]
    legend = ax.legend(handles=legend_elements, loc='upper right', 
                       fontsize=11, facecolor='#0a3d62', edgecolor='#00d4ff',
                       labelcolor='white')
    legend.get_frame().set_alpha(0.9)
    
    # Add annotation box with key insight
    textstr = ('Key Insight:\n'
               'At β ≥ 2.6, optimal strategy\n'
               'shifts from heavy DGU usage\n'
               'to maximum load shedding,\n'
               'drastically cutting CO₂')
    props = dict(boxstyle='round,pad=0.8', facecolor='#0a3d62', 
                 edgecolor='#00d4ff', alpha=0.9)
    ax.text(0.02, 0.02, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='bottom', bbox=props, color='#e0e0e0',
            fontfamily='monospace')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, facecolor=fig.get_facecolor(),
                edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"[OK] Pareto frontier saved to: {output_path}")


def create_beta_comparison_plot(data, output_path):
    """Create a bar chart comparing costs at different β values."""
    
    beta_sweep = data['beta_sweep']
    
    betas = [b['beta'] for b in beta_sweep]
    totals = [b['total'] for b in beta_sweep]
    financials = [b['financial'] for b in beta_sweep]
    co2s = [b['co2'] for b in beta_sweep]
    dgus = [b['x_dgu'] for b in beta_sweep]
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.patch.set_facecolor('#1a1a2e')
    
    for ax in axes.flat:
        ax.set_facecolor('#16213e')
        ax.tick_params(colors='white', labelsize=10)
        for spine in ax.spines.values():
            spine.set_color('#555555')
        ax.grid(True, alpha=0.15, color='white', axis='y', linestyle='--')
    
    # Plot 1: Total Loss vs β
    colors1 = plt.cm.plasma(np.linspace(0.2, 0.9, len(betas)))
    axes[0,0].bar(range(len(betas)), totals, color=colors1, edgecolor='white', linewidth=0.5)
    axes[0,0].set_xticks(range(len(betas)))
    axes[0,0].set_xticklabels([f'β={b:.1f}' for b in betas], rotation=45, color='white')
    axes[0,0].set_ylabel('Total Loss ($/hr)', color='white', fontweight='bold')
    axes[0,0].set_title('Total Loss vs β', color='white', fontweight='bold', fontsize=13)
    
    # Plot 2: DGU MW vs β
    axes[0,1].bar(range(len(betas)), dgus, color='#ff6b6b', edgecolor='white', linewidth=0.5)
    axes[0,1].set_xticks(range(len(betas)))
    axes[0,1].set_xticklabels([f'β={b:.1f}' for b in betas], rotation=45, color='white')
    axes[0,1].set_ylabel('DGU Dispatch (MW)', color='white', fontweight='bold')
    axes[0,1].set_title('DGU Usage vs β', color='white', fontweight='bold', fontsize=13)
    
    # Plot 3: CO₂ vs β
    axes[1,0].bar(range(len(betas)), co2s, color='#51cf66', edgecolor='white', linewidth=0.5)
    axes[1,0].set_xticks(range(len(betas)))
    axes[1,0].set_xticklabels([f'β={b:.1f}' for b in betas], rotation=45, color='white')
    axes[1,0].set_ylabel('CO₂ Emissions (tonnes)', color='white', fontweight='bold')
    axes[1,0].set_title('CO₂ Emissions vs β', color='white', fontweight='bold', fontsize=13)
    
    # Plot 4: Financial vs Carbon cost breakdown
    carbon_costs = [b['total'] - b['financial'] for b in beta_sweep]
    x = range(len(betas))
    axes[1,1].bar(x, financials, color='#00d4ff', edgecolor='white', linewidth=0.5, 
                  label='Financial Cost')
    axes[1,1].bar(x, carbon_costs, bottom=financials, color='#e040fb', edgecolor='white',
                  linewidth=0.5, label='β×CO₂ Penalty')
    axes[1,1].set_xticks(range(len(betas)))
    axes[1,1].set_xticklabels([f'β={b:.1f}' for b in betas], rotation=45, color='white')
    axes[1,1].set_ylabel('Cost ($/hr)', color='white', fontweight='bold')
    axes[1,1].set_title('Cost Breakdown vs β', color='white', fontweight='bold', fontsize=13)
    legend = axes[1,1].legend(facecolor='#0a3d62', edgecolor='#00d4ff', labelcolor='white')
    
    fig.suptitle('AI Dispatcher: β Sensitivity Analysis — 90 MW Deficit',
                 fontsize=16, color='white', fontweight='bold', y=1.02)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, facecolor=fig.get_facecolor(),
                edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"[OK] Beta comparison saved to: {output_path}")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pareto_file = os.path.join(script_dir, "pareto_data.json")
    
    if not os.path.exists(pareto_file):
        print("[ERROR] Run optimizer.py first to generate pareto_data.json")
        sys.exit(1)
    
    data = load_pareto_data(pareto_file)
    
    if HAS_MPL:
        # Generate Pareto frontier plot
        pareto_img = os.path.join(script_dir, "pareto_frontier.png")
        create_pareto_plot(data, pareto_img)
        
        # Generate beta comparison plot
        beta_img = os.path.join(script_dir, "beta_sensitivity.png")
        create_beta_comparison_plot(data, beta_img)
    else:
        print("Pareto Frontier Data (for manual plotting):")
        for p in data['pareto_frontier']:
            print(f"  Financial: ${p['financial']:>10,.0f}  CO₂: {p['co2']:>6.1f}t  "
                  f"DGU={p['x_dgu']}  HVAC={p['x_hvac']}  PUMP={p['x_pump']}  MILL={p['x_mill']}")
