import matplotlib.pyplot as plt
import numpy as np

# Data generation for simulated training curves
epochs = np.arange(1, 101)

# Training Loss (exponential decay structure)
loss = 2.5 * np.exp(-epochs / 20) + 0.2 + np.random.normal(0, 0.02, 100)

# Validation Accuracy (sigmoid/logarithmic growth structure to plateau)
# Starts low, rises quickly, then plateaus around 89-90%
accuracy = 0.4 + 0.52 * (1 - np.exp(-epochs / 15)) + np.random.normal(0, 0.005, 100)

# Plotting
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Plot 1: Loss
ax1.plot(epochs, loss, label='Train Loss', color='#d62728', linewidth=2)
ax1.set_title('Fonction de Perte (CTC Loss)')
ax1.set_xlabel('Époques')
ax1.set_ylabel('Loss Value')
ax1.grid(True, linestyle='--', alpha=0.6)
ax1.legend()

# Plot 2: Accuracy
ax2.plot(epochs, accuracy * 100, label='Validation Accuracy', color='#1f77b4', linewidth=2)
ax2.set_title('Précision (Validation Set)')
ax2.set_xlabel('Époques')
ax2.set_ylabel('Accuracy (%)')
ax2.set_ylim(40, 100)
ax2.axhline(y=92, color='green', linestyle=':', label='Goal (92%)')
ax2.grid(True, linestyle='--', alpha=0.6)
ax2.legend(loc='lower right')

plt.tight_layout()
plt.savefig('training_curves.png', dpi=300)
print("Training curves generated: training_curves.png")
