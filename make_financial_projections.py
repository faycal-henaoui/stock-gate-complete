import matplotlib.pyplot as plt
import numpy as np

# Financial Data (in DZD)
capex = 1160000        # Initial Investment
opex_monthly = 140000  # Monthly fixed costs
target_mrr = 345000    # Target Monthly Recurring Revenue at Month 6

# Simulation for 12 Months
months = np.arange(0, 13)
revenue = []
cumulative_cashflow = []
current_balance = -capex

# Ramp up strategy: We start selling in Month 1, reach target in Month 6
for m in months:
    if m == 0:
        rev = 0
        exp = 0 # Initial investment already counted in start balance
    else:
        # Linear growth of revenue from Month 1 to 6, then stable
        if m <= 6:
            percent_target = m / 6.0
        else:
            percent_target = 1.0
        
        rev = target_mrr * percent_target
        exp = opex_monthly
        
        # Profit for this month
        profit = rev - exp
        current_balance += profit
    
    revenue.append(rev)
    cumulative_cashflow.append(current_balance)

# Create the visualization
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Plot 1: Revenue vs Costs (Operational View)
ax1.plot(months[1:], [opex_monthly]*12, 'r--', linewidth=2, label='Coûts Fixes (OPEX)')
ax1.plot(months[1:], revenue[1:], 'g-', linewidth=2, marker='o', label='Revenus (MRR)')
ax1.fill_between(months[1:], [opex_monthly]*12, revenue[1:], where=(np.array(revenue[1:]) > opex_monthly), interpolate=True, color='green', alpha=0.1, label='Zone de Profit')
ax1.fill_between(months[1:], [opex_monthly]*12, revenue[1:], where=(np.array(revenue[1:]) <= opex_monthly), interpolate=True, color='red', alpha=0.1, label='Zone de Perte')

ax1.set_title('Évolution du Revenu Mensuel vs Coûts', fontsize=12, fontweight='bold')
ax1.set_xlabel('Mois (Année 1)')
ax1.set_ylabel('Montant (DZD)')
ax1.grid(True, linestyle='--', alpha=0.6)
ax1.legend()
ax1.set_xticks(months[1:])

# Plot 2: ROI & Break-even (Investment View)
# Highlight the zero line
ax2.axhline(y=0, color='black', linewidth=1.5)
ax2.plot(months, cumulative_cashflow, 'b-', linewidth=2.5, marker='D', label='Trésorerie Cumulée (Cash Flow)')

# Find crossing point (approx)
# We see it crosses somewhere between Month 6 and 8 in this ramp-up model
# In the simplified text model (instant 345k), it was 6 months. 
# With ramp-up, it will be later. Let's adjust text if needed or just show the graph.
# Let's keep the graph honest to the ramp-up.

# Annotate Break-even
break_even_idx = np.where(np.array(cumulative_cashflow) > 0)[0][0]
ax2.annotate('Point Mort (Break-even)\nROI Atteint', 
             xy=(break_even_idx, cumulative_cashflow[break_even_idx]), 
             xytext=(break_even_idx-4, cumulative_cashflow[break_even_idx]+250000), # Moved left and down
             arrowprops=dict(facecolor='black', shrink=0.05),
             fontsize=10, fontweight='bold', ha='center')

# Add padding to top of y-axis to ensure text fits
y_min, y_max = ax2.get_ylim()
ax2.set_ylim(y_min, y_max * 1.2) # +20% headroom

ax2.set_title("Retour sur Investissement (ROI)", fontsize=12, fontweight='bold')
ax2.set_xlabel('Mois d\'activité')
ax2.set_ylabel('Balance Cumulée (DZD)')
ax2.grid(True, linestyle='--', alpha=0.6)
ax2.legend()
ax2.set_xticks(months)

# Format Y axis to K/M
from matplotlib.ticker import FuncFormatter
def currency(x, pos):
    if abs(x) >= 1000000:
        return f'{x*1e-6:1.1f}M'
    return f'{x*1e-3:.0f}K'

ax1.yaxis.set_major_formatter(FuncFormatter(currency))
ax2.yaxis.set_major_formatter(FuncFormatter(currency))

plt.tight_layout()
plt.savefig('financial_projections.png', dpi=300)
print("Image generated: financial_projections.png")
