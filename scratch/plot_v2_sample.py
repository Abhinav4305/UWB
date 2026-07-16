import numpy as np
import matplotlib.pyplot as plt
import sys
import os

def plot_sample():
    filepath = r"c:\RR_02\gesture_dataset_v2\G01_SWIPE_LR\trial_1783401397.npy"
    data = np.load(filepath) # Shape: (100, 2, 2, 96) complex64
    
    # Extract the middle 64 frames (like the network sees)
    window = data[18:82] 
    
    # Extract the 8 channels
    tx0_rx0 = window[:, 0, 0, :]
    tx0_rx1 = window[:, 0, 1, :]
    tx1_rx0 = window[:, 1, 0, :]
    tx1_rx1 = window[:, 1, 1, :]
    
    channels = [
        ("TX0_RX0 Real", np.real(tx0_rx0)),
        ("TX0_RX0 Imag", np.imag(tx0_rx0)),
        ("TX0_RX1 Real", np.real(tx0_rx1)),
        ("TX0_RX1 Imag", np.imag(tx0_rx1)),
        ("TX1_RX0 Real", np.real(tx1_rx0)),
        ("TX1_RX0 Imag", np.imag(tx1_rx0)),
        ("TX1_RX1 Real", np.real(tx1_rx1)),
        ("TX1_RX1 Imag", np.imag(tx1_rx1)),
    ]
    
    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    fig.suptitle("V2 Gesture Sample: SWIPE_LR (8 Channels of Data!)", fontsize=16, fontweight='bold')
    
    for i, (title, ch_data) in enumerate(channels):
        ax = axes[i // 4, i % 4]
        # Plot time vs range bins
        im = ax.imshow(ch_data.T, aspect='auto', cmap='viridis', origin='lower')
        ax.set_title(title)
        ax.set_xlabel("Time (Frames)")
        ax.set_ylabel("Range Bins")
        plt.colorbar(im, ax=ax)
        
    plt.tight_layout()
    out_path = r"C:\Users\Admin\.gemini\antigravity-ide\brain\2281aa1e-4f25-4be8-95ed-a0aeeb18cc52\v2_sample.png"
    plt.savefig(out_path)
    print(f"Saved plot to {out_path}")

if __name__ == "__main__":
    plot_sample()
