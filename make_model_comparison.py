import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# Configure figure
fig, ax = plt.subplots(figsize=(10, 5))
ax.axis('off')

# Title
ax.text(5, 4.5, "Comparative Analysis: CRNN (LSTM) vs SVTR (Transformer)", 
        ha='center', va='center', fontsize=14, fontweight='bold', color='#333333')

# Scenario Description
ax.text(5, 4.0, "Scenario: Irregular spacing and local noise (Thermal Receipt)", 
        ha='center', va='center', fontsize=10, style='italic', color='#666666')

# --- Visualizing the Logic ---

# 1. Input Image Representation (Middle)
# Draw a "receipt text" box with some visual "noise"
ax.add_patch(Rectangle((3.5, 2.5), 3, 1, fill=True, color='#f0f0f0', ec='gray'))
ax.text(5, 3.0, "T O  T  A   L", 
        ha='center', va='center', fontsize=20, family='monospace', fontweight='bold')
# Add some "noise" dots
ax.plot([3.8, 3.9, 4.2, 5.5, 6.1], [2.6, 3.3, 2.7, 3.2, 2.9], 'k.', markersize=2, alpha=0.5)

# 2. CRNN (Left Side)
ax.text(1.5, 3.0, "Legacy Architecture\n(CRNN + LSTM)", 
        ha='center', va='center', fontsize=11, fontweight='bold', color='#D9534F')

# Draw arrow
ax.arrow(3.4, 3.0, -1.0, 0, head_width=0.1, head_length=0.1, fc='#D9534F', ec='#D9534F')

ax.text(1.5, 2.2, "Sequential Processing\n(Slice by Slice)", 
        ha='center', va='center', fontsize=9, color='#555555')

# Result Box
ax.add_patch(Rectangle((0.5, 1.2), 2, 0.8, fill=True, color='#f9f2f4', ec='#D9534F'))
ax.text(1.5, 1.6, 'Prediction: "T0 TAL"', 
        ha='center', va='center', fontsize=12, family='monospace', color='#D9534F')
ax.text(1.5, 0.8, "Failure: Context Lost\ndue to gaps", 
        ha='center', va='center', fontsize=9, color='#D9534F')


# 3. SVTR (Right Side)
ax.text(8.5, 3.0, "Our Choice\n(SVTR Transformer)", 
        ha='center', va='center', fontsize=11, fontweight='bold', color='#28a745')

# Draw arrow
ax.arrow(6.6, 3.0, 1.0, 0, head_width=0.1, head_length=0.1, fc='#28a745', ec='#28a745')

ax.text(8.5, 2.2, "Global Attention\n(2D Mixing)", 
        ha='center', va='center', fontsize=9, color='#555555')

# Result Box
ax.add_patch(Rectangle((7.5, 1.2), 2, 0.8, fill=True, color='#e8f5e9', ec='#28a745'))
ax.text(8.5, 1.6, 'Prediction: "TOTAL"', 
        ha='center', va='center', fontsize=12, family='monospace', color='#28a745')
ax.text(8.5, 0.8, "Success: Global Shape\nRecognition", 
        ha='center', va='center', fontsize=9, color='#28a745')

plt.tight_layout()
plt.savefig('svtr_vs_crnn.png', dpi=300)
print("Comparison image generated: svtr_vs_crnn.png")
