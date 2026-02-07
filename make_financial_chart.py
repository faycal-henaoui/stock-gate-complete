import matplotlib.pyplot as plt
import numpy as np

# Data
categories = ['Vitesse de Traitement', 'Coût par Document', 'Taux d\'Erreur', 'Validation Directe']
manual = [180, 2.50, 4.0, 0] # 180 sec, 2.50$, 4% error, 0% automated
automated = [5, 0.15, 0.5, 85] # 5 sec, 0.15$, 0.5% error, 85% automated

# Normalize for radar chart or use Bar chart? 
# A grouped bar chart with dual axis is better for mixed units, but let's do separate or subplots.
# Let's do a simple component Comparison: Manual vs Auto for "Time" and "Cost".

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# 1. Processing Time Comparison
labels_time = ['Saisie Manuelle', 'Notre Solution']
times = [3.5, 0.1] # Minutes
colors_time = ['#e74c3c', '#2ecc71']

bars = ax1.bar(labels_time, times, color=colors_time, width=0.5)
ax1.set_title('Temps de Traitement Moyen (Minutes)', fontsize=12, fontweight='bold')
ax1.set_ylabel('Temps (min)')
ax1.grid(axis='y', linestyle='--', alpha=0.5)

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
             f'{height} min',
             ha='center', va='bottom', fontsize=11, fontweight='bold')

# 2. Cost Reduction Estimation (per 1000 invoices)
# Assumptions: SMIC or standard clerk salary ~10$/hour. 
# Manual: 3.5 min/invoice -> ~17 invoices/hr -> ~0.58$ per invoice
# Auto: Server cost negligible per invoice -> ~0.02$
labels_cost = ['Coût (1000 Factures)']
cost_manual = 580 # $
cost_auto = 20 # $

x = np.arange(len(labels_cost))
width = 0.35

rects1 = ax2.bar(x - width/2, [cost_manual], width, label='Saisie Manuelle', color='#e74c3c')
rects2 = ax2.bar(x + width/2, [cost_auto], width, label='Notre Solution', color='#2ecc71')

ax2.set_title("Coût Estimé pour 1000 Factures ($)", fontsize=12, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(labels_cost)
ax2.legend()
ax2.grid(axis='y', linestyle='--', alpha=0.5)

# Add labels
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax2.text(rect.get_x() + rect.get_width()/2., height,
                 f'{height} $',
                 ha='center', va='bottom', fontsize=11, fontweight='bold')

autolabel(rects1)
autolabel(rects2)

plt.tight_layout()
plt.savefig('economic_impact.png', dpi=300)
print("Image generated: economic_impact.png")
