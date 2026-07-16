import numpy as np
from pathlib import Path

def test_motion():
    files = list(Path(r"c:\RR_02\gesture_dataset_v2\G01_SWIPE_LR").glob("*.npy"))
    if not files: return
    
    for f in files[:20]:
        data = np.load(f)
        
        empty = data[:30]
        swipe = data[40:70]
        
        empty_delta = np.mean(np.abs(empty[1:] - empty[:-1]))
        swipe_delta = np.mean(np.abs(swipe[1:] - swipe[:-1]))
        
        print(f"File: {f.name} | Empty Delta: {empty_delta:.6f} | Swipe Delta: {swipe_delta:.6f}")

if __name__ == "__main__":
    test_motion()
