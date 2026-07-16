import numpy as np
from pathlib import Path

def check_mti():
    files = list(Path(r"c:\RR_02\gesture_dataset_v2\G01_SWIPE_LR").glob("*.npy"))
    if not files: return
    
    for f in files[:20]:
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
        
        # MTI
        stacked = stacked - np.mean(stacked, axis=1, keepdims=True)
        
        # Check first 20 frames (empty room)
        empty_std = np.std(stacked[:, :20, :])
        
        # Check middle 20 frames (swipe)
        swipe_std = np.std(stacked[:, 40:60, :])
        
        print(f"File: {f.name} | Empty MTI STD: {empty_std:.6f} | Swipe MTI STD: {swipe_std:.6f}")

if __name__ == "__main__":
    check_mti()
