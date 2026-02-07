import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

# Configure figure
fig, ax = plt.subplots(figsize=(10, 6))

# Axis setup
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_xlabel('Robustesse aux variations de Layout', fontsize=12, fontweight='bold', labelpad=10)
ax.set_ylabel('Efficacité (Vitesse & Faible Coût)', fontsize=12, fontweight='bold', labelpad=10)
ax.set_title("Positionnement de notre approche Hybride", fontsize=14, fontweight='bold', pad=20)

# 1. Regex Area (Bottom Left)
# Fast but not robust
ax.add_patch(Ellipse((20, 90), width=25, height=15, color='#d9534f', alpha=0.3))
ax.text(20, 90, "Approche Standard\n(Regex / Zonal)", 
        ha='center', va='center', fontsize=11, fontweight='bold', color='#c9302c')
ax.text(20, 80, "Rapide mais\nCassant (Brittle)", 
        ha='center', va='center', fontsize=9, style='italic', color='#555')

# 2. Donut/LLM Area (Bottom Right)
# Robust but slow/expensive
ax.add_patch(Ellipse((85, 20), width=25, height=15, color='#f0ad4e', alpha=0.3))
ax.text(85, 20, "End-to-End AI\n(Donut / LLM)", 
        ha='center', va='center', fontsize=11, fontweight='bold', color='#ec971f')
ax.text(85, 10, "Puissant mais\nLent & Hallucinations", 
        ha='center', va='center', fontsize=9, style='italic', color='#555')

# 3. Our Solution (Top Right)
# The Sweet Spot
ax.add_patch(Ellipse((80, 85), width=30, height=20, color='#5cb85c', alpha=0.4))
ax.text(80, 85, "Notre Solution\n(Spatial + Sémantique)", 
        ha='center', va='center', fontsize=12, fontweight='bold', color='#4cae4c')
ax.text(80, 75, "Robustesse Structurelle\n+ Temps Réel", 
        ha='center', va='center', fontsize=9, style='italic', color='#2b542c')

# Annotations / Arrows
ax.annotate("", xy=(65, 85), xytext=(35, 90),
            arrowprops=dict(arrowstyle="->", color="gray", lw=1.5, linestyle="--"))
ax.text(50, 93, "Meilleure gestion\ndu 'Multi-lignes'", ha='center', fontsize=8, color='gray')

ax.annotate("", xy=(80, 70), xytext=(85, 30),
            arrowprops=dict(arrowstyle="->", color="gray", lw=1.5, linestyle="--"))
ax.text(92, 50, "Sans entraînement\nlourd ni GPU", ha='center', fontsize=8, color='gray')

# Grid
ax.grid(True, linestyle=':', alpha=0.4)

# Remove ticks for conceptual chart
ax.set_xticks([])
ax.set_yticks([])

plt.tight_layout()
plt.savefig('algo_comparison.png', dpi=300)
print("Algorithm comparison image generated: algo_comparison.png")
