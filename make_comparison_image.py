import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.patches import Rectangle
import os

# 1. Setup paths
input_image = "blury_crop.jpg"  # You must save your crop with this name!
output_image = "finetuning_comparison.png"

# 2. Configure the plot
fig, ax = plt.subplots(figsize=(10, 4))
ax.axis('off')

# 3. Load the image or create a placeholder
if os.path.exists(input_image):
    img = mpimg.imread(input_image)
    # Display image centered
    ax.imshow(img, aspect='auto', extent=[2, 8, 5, 8])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
else:
    # Placeholder if user hasn't saved the file yet
    ax.text(5, 7, "IMAGE NOT FOUND\nSave your crop as 'blury_crop.jpg'", 
            ha='center', va='center', fontsize=14, color='gray')
    ax.add_patch(Rectangle((2, 5), 6, 3, fill=False, edgecolor='gray', linestyle='--'))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)

# 4. Add "Context" Label
ax.text(5, 8.5, "Input: Real Invoice Crop (Low Resolution / Noise)", 
        ha='center', va='center', fontsize=12, fontweight='bold', color='#333333')

# 5. Add Predictions Section
# Draw a separator line
ax.plot([1, 9], [4.5, 4.5], color='#dddddd', linewidth=1)

# --- Standard Model Side (Left) ---
ax.text(2.5, 3.5, "Standard OCR (Base Model)", 
        ha='center', va='center', fontsize=11, fontweight='bold', color='#555555')

# The "Wrong" Prediction
ax.text(2.5, 2.0, '"Adre se : / Tel"', 
        ha='center', va='center', fontsize=16, family='monospace', 
        color='#D9534F', backgroundcolor='#f9f2f4') # Red-ish text

ax.text(2.5, 1.0, "Result: Split word / Noise", 
        ha='center', va='center', fontsize=9, style='italic', color='#D9534F')


# --- Fine-tuned Model Side (Right) ---
ax.text(7.5, 3.5, "Fine-tuned SVTR (Our Solution)", 
        ha='center', va='center', fontsize=11, fontweight='bold', color='#28a745')

# The "Correct" Prediction
ax.text(7.5, 2.0, '"Adresse : / Tel"', 
        ha='center', va='center', fontsize=16, family='monospace', 
        color='#28a745', backgroundcolor='#e8f5e9') # Green-ish text

ax.text(7.5, 1.0, "Result: Corrected via Fine-tuning", 
        ha='center', va='center', fontsize=9, style='italic', color='#28a745')

# 6. Save
plt.tight_layout()
plt.savefig(output_image, dpi=300, bbox_inches='tight')
print(f"Successfully created comparison image: {os.path.abspath(output_image)}")
