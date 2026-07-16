import numpy as np
from pathlib import Path

def test_energy():
    files = list(Path(r"c:\RR_02\gesture_dataset_v2").rglob("*.npy"))
    if not files: return
    
    max_energies = []
    for f in files:
        data = np.load(f)
        frame_energy = np.sum(np.abs(data), axis=(1, 2, 3))
        max_energies.append(np.max(frame_energy))
        
    print(f"Min peak: {np.min(max_energies):.1f} | Max peak: {np.max(max_energies):.1f} | Median: {np.median(max_energies):.1f}")

if __name__ == "__main__":
    test_energy()
