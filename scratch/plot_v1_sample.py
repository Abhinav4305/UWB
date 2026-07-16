import numpy as np
import matplotlib.pyplot as plt
import os

def plot_old_sample():
    filepath = r"c:\RR_02\gesture_dataset\G01_SWIPE_LR\subject_01_trial_001_1782799553999.npy"
    data = np.load(filepath) # Shape: (Time, 2, 96) complex64
    
    # Extract middle 64 frames
    if data.shape[0] >= 64:
        start = (data.shape[0] - 64) // 2
        window = data[start:start+64] 
    else:
        window = data
        
    rx1 = window[:, 0, :]
    rx2 = window[:, 1, :]
    
    channels = [
        ("Averaged I (np.real)", np.real(rx1)),
        ("BLANK (np.imag)", np.imag(rx1)),
        ("Averaged Q (np.real)", np.real(rx2)),
        ("BLANK (np.imag)", np.imag(rx2)),
    ]
    
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    fig.suptitle("V1 Gesture Sample (The BUGGY data!)", fontsize=16, fontweight='bold')
    
    for i, (title, ch_data) in enumerate(channels):
        ax = axes[i]
        im = ax.imshow(ch_data.T, aspect='auto', cmap='viridis', origin='lower')
        ax.set_title(title)
        ax.set_xlabel("Time (Frames)")
        if i == 0:
            ax.set_ylabel("Range Bins")
        plt.colorbar(im, ax=ax)
        
    plt.tight_layout()
    out_path = r"C:\Users\Admin\.gemini\antigravity-ide\brain\2281aa1e-4f25-4be8-95ed-a0aeeb18cc52\v1_sample.png"
    plt.savefig(out_path)
    print(f"Saved plot to {out_path}")

if __name__ == "__main__":
    plot_old_sample()
