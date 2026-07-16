import os
import sys
import argparse
import time
import threading
import queue
from pathlib import Path
import numpy as np

# Suppress warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

os.add_dll_directory(r"C:\RR_02\bin") 

_DEMO_DIR = r"C:\RR_02\novelda-uwb-demos\Demos\RadarDirect\X7RadarDirectCallback"
_DEMO_PARENT = r"C:\RR_02\novelda-uwb-demos\Demos"
for path in [_DEMO_PARENT, _DEMO_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

from radar_direct_callback import RadarDirectCallback

# ── CONFIG ──────────────────────────────────────────────────────────────
RANGE_BINS = 96
RADAR_FPS  = 40   

GESTURE_CLASSES = {
    "1":  ("G01_SWIPE_LR", "Left -> Right swipe"),
    "2":  ("G02_SWIPE_RL", "Right -> Left swipe"),
    "3":  ("G03_SWIPE_UD", "Up -> Down swipe"),
    "4":  ("G04_SWIPE_DU", "Down -> Up swipe"),
}

# ── RADAR SOURCE ────────────────────────────────────────────────────────
class X7Radar:
    def __init__(self, preset_json_path=None):
        self.frame_queue = queue.Queue(maxsize=400)
        self.range_bins = RANGE_BINS
        
        # Buffer to combine TX0 and TX1 into a single frame: (TX, RX, BINS)
        self.virtual_frame = np.zeros((2, 2, RANGE_BINS), dtype=np.complex64)
        self.last_tx_data = [False, False]
        
        if preset_json_path is None:
            preset_json_path = r"C:\RR_02\novelda-uwb-demos\Demos\RadarDirect\X7RadarDirectCallback\Presets\default_preset.json"
        
        self.radar_runner = RadarDirectCallback()
        self._thread = threading.Thread(target=self.radar_runner.run_with_callback_preset, 
                                        args=(self._frame_callback, preset_json_path), daemon=True)
        self._thread.start()
        print("[INFO] X7 PySignalFlow background stream started.")

    def _frame_callback(self, trx_mask, data, seq_num, timestamp, range_offset, bin_length):
        try:
            tx_idx = int(trx_mask[1])
            radar_data = np.asarray(data, dtype=np.float32)
            
            if radar_data.shape[2] > self.range_bins:
                radar_data = radar_data[:, :, :self.range_bins]
                
            # Properly combine the float I and Q into complex numbers!
            complex_data = (radar_data[:, 0, :] + 1j * radar_data[:, 1, :]).astype(np.complex64)
            self.virtual_frame[tx_idx, :, :] = complex_data
            self.last_tx_data[tx_idx] = True
            
            # Only push to queue when we have BOTH tx0 and tx1
            if all(self.last_tx_data):
                if not self.frame_queue.full():
                    self.frame_queue.put(self.virtual_frame.copy())
                self.last_tx_data = [False, False]
        except Exception as e:
            pass
        return True

    def get_frame(self):
        try: return self.frame_queue.get(timeout=2.0)
        except queue.Empty: return None
        
    def flush_queue(self):
        while not self.frame_queue.empty():
            try: self.frame_queue.get_nowait()
            except: break

    def close(self): 
        print("[INFO] X7 radar closed.")

# ── RECORDING LOGIC ─────────────────────────────────────────────────────
def record_trial(radar, duration_s, label):
    time.sleep(1.0) # Give user a second to get ready
    
    # Empty the buffer right before recording so we don't grab old frames
    radar.flush_queue()
    
    n_frames = int(duration_s * RADAR_FPS)
    frames = np.zeros((n_frames, 2, 2, RANGE_BINS), dtype=np.complex64)
    collected = 0
    print(f"\n  ▶ Recording '{label}' for {duration_s}s...", end="")
    
    while collected < n_frames:
        frame = radar.get_frame()
        if frame is not None:
            frames[collected] = frame
            collected += 1
            if collected % 10 == 0:
                print(f"\r  ▶ Recording '{label}' ... {collected}/{n_frames}", end="", flush=True)
        else:
            print(f"\n[WARN] Timeout: No frame received. Check radar connection.", end="", flush=True)
            break
            
    print("\n  ▶ Recording complete!")
    return frames[:collected]

def run_gesture(args, radar):
    print("\nStarting Gesture Recording Session...")
    for k, v in GESTURE_CLASSES.items():
        print(f"  [{k}] - {v[1]}")
        
    choice = input("\nEnter gesture ID (1-4): ")
    if choice not in GESTURE_CLASSES: 
        print("Invalid choice.")
        return
        
    folder, desc = GESTURE_CLASSES[choice]
    out_dir = Path(args.out) / folder
    
    # Record for 2.5 seconds like original script
    data = record_trial(radar, 2.5, desc)
    if len(data) > 0:
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = f"trial_{int(time.time())}.npy"
        np.save(out_dir / filename, data)
        print(f"\nSaved {len(data)} frames to {out_dir / filename}")

# ── ENTRY POINT ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="gesture_dataset_v2")
    args = parser.parse_args()
    
    radar = X7Radar()
    try:
        run_gesture(args, radar)
    finally:
        radar.close()
