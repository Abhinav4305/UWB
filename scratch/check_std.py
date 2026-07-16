import numpy as np
import os
from pathlib import Path

def check_std():
    files = list(Path(r"c:\RR_02\gesture_dataset_v2\G01_SWIPE_LR").glob("*.npy"))
    if not files: return
    
    for f in files:
        data = np.load(f)
        tx0_rx0 = data[:, 0, 0, :]
        tx0_rx1 = data[:, 0, 1, :]
        tx1_rx0 = data[:, 1, 0, :]
        tx1_rx1 = data[:, 1, 1, :]
        
        stacked = np.stack([
            np.real(tx0_rx0), np.imag(tx0_rx0),
            np.real(tx0_rx1), np.imag(tx0_rx1),
            np.real(tx1_rx0), np.imag(tx1_rx0),
            np.real(tx1_rx1), np.imag(tx1_rx1)
        ], axis=0)
        
        # Check first 20 frames (likely empty room before swipe)
        empty_std = np.std(stacked[:, :20, :])
        
        # Check middle 20 frames (likely the actual swipe)
        swipe_std = np.std(stacked[:, 40:60, :])
        
        print(f"File: {f.name} | Empty STD: {empty_std:.6f} | Swipe STD: {swipe_std:.6f}")

if __name__ == "__main__":
    check_std()
