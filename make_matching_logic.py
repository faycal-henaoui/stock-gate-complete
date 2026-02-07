import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

# Configure figure
fig, ax = plt.subplots(figsize=(12, 7))
ax.axis('off')
ax.set_title("Logique de 'Smart Matching' (Réconciliation Produit)", fontsize=16, fontweight='bold', pad=20)

# Set explicit limits to prevent scaling issues
ax.set_xlim(0, 12)
ax.set_ylim(0, 7)

# Colors
qc_color = '#d9edf7' # Query
db_color = '#dff0d8' # DB
algo_color = '#fcf8e3' # Algo
result_color = '#f2dede' # Result

# 1. Input (Invoice Text)
ax.add_patch(Rectangle((0.5, 4.5), 2.5, 1, color=qc_color, ec='#31708f'))
ax.text(1.75, 5.0, 'Input Facture:\n"Ecran 24p Dell"', ha='center', va='center', fontsize=11)

# 2. Strategy 1: Exact Memory (Cache)
ax.add_patch(Rectangle((3.5, 5.2), 3.5, 1.0, color=db_color, ec='#3c763d'))
ax.text(5.25, 5.7, '1. Mapping Mémoire\n(Base de Connaissance)', ha='center', va='center', fontsize=10, fontweight='bold')

# Arrow 1
ax.annotate("", xy=(3.5, 5.7), xytext=(3.0, 5.0),
            arrowprops=dict(arrowstyle="->", color="gray", lw=1.5))

# Decision Diamond 1 (implied by text)
ax.text(7.3, 5.7, "Trouvé ?", fontsize=9, style='italic') # Moved left
# Arrow to Finish
ax.annotate("Oui", xy=(9.5, 5.7), xytext=(8.2, 5.7), # Moved start right
            arrowprops=dict(arrowstyle="->", color="green", lw=1.5))
ax.add_patch(Rectangle((9.5, 5.2), 1.5, 1.0, color='#e8f5e9', ec='green'))
ax.text(10.25, 5.7, "VALIDATION\nAUTOMATIQUE", ha='center', va='center', fontsize=9, fontweight='bold', color='green')


# 2. Strategy 2: Fuzzy Logic (Fallback)
# Arrow down
ax.annotate("", xy=(5.25, 4.2), xytext=(5.25, 5.2),
            arrowprops=dict(arrowstyle="->", color="red", lw=1.5))
# Text "Non" next to arrow
ax.text(5.35, 4.7, "Non", fontsize=9, color="red")

ax.add_patch(Rectangle((3.5, 2.5), 3.5, 1.7, color=algo_color, ec='#8a6d3b'))
ax.text(5.25, 3.8, '2. Moteur de Similarité', ha='center', va='center', fontsize=11, fontweight='bold')
ax.text(5.25, 3.2, 'Score = 0.7*Levenshtein\n+ 0.3*Jaccard', ha='center', va='center', fontsize=9)

# Database Context
ax.add_patch(Rectangle((3.5, 1.0), 3.5, 1.0, color='#f5f5f5', ec='gray', linestyle='--'))
ax.text(5.25, 1.5, 'Stock Database\n(10,000 products)', ha='center', va='center', fontsize=10, color='gray')
ax.annotate("", xy=(5.25, 2.5), xytext=(5.25, 2.0), arrowprops=dict(arrowstyle="->", color="gray", linestyle=":"))

# 3. Output Predictions
ax.annotate("Top-K", xy=(7.5, 3.35), xytext=(7.0, 3.35),
            arrowprops=dict(arrowstyle="->", color="gray", lw=1.5))

ax.add_patch(Rectangle((8.0, 2.3), 3.0, 2.1, color=result_color, ec='#a94442'))
ax.text(9.5, 3.9, 'Suggestions (Humain)', ha='center', va='center', fontsize=11, fontweight='bold')
ax.text(9.5, 3.4, '1. Dell Monitor 24" (92%)', ha='center', va='center', fontsize=9)
ax.text(9.5, 2.9, '2. Dell Screen 22" (65%)', ha='center', va='center', fontsize=9)
ax.text(9.5, 2.5, '3. Cable 24 pin (12%)', ha='center', va='center', fontsize=9)

# 4. Human Feedback Loop
# Curve from result back to memory
ax.annotate("Validation Humaine", xy=(5.25, 0.5), xytext=(9.5, 2.0),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.3", color="blue", lw=1.5, linestyle="--"))

ax.text(5.25, 0.3, "Mise à jour du Mapping (Apprentissage)", ha='center', va='center', fontsize=10, color="blue", fontweight='bold')

# Curve up to memory
ax.annotate("", xy=(3.5, 5.5), xytext=(5.25, 0.5),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.5", color="blue", lw=1, linestyle="--"))

# Remove tight_layout to respect axes limits
# plt.tight_layout()
plt.savefig('smart_matching_logic.png', dpi=300, bbox_inches='tight')
print("Image generated: smart_matching_logic.png")
