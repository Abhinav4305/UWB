import os
os.add_dll_directory(r"C:\RR_02\bin") 

import sys
_DEMO_DIR = r"C:\RR_02\novelda-uwb-demos\Demos\RadarDirect\X7RadarDirectCallback"
_DEMO_PARENT = r"C:\RR_02\novelda-uwb-demos\Demos"
for path in [_DEMO_PARENT, _DEMO_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

import argparse
import time
import threading
import queue
from pathlib import Path
import numpy as np
from radar_direct_callback import RadarDirectCallback

# ── CONFIG ──────────────────────────────────────────────────────────────
RANGE_BINS = 192    
RADAR_FPS  = 40   

GESTURE_CLASSES = {
    "1":  ("G01_SWIPE_LR", "Left -> Right swipe"),
    "2":  ("G02_SWIPE_RL", "Right -> Left swipe"),
}

# ── RADAR SOURCE ────────────────────────────────────────────────────────
class X7Radar:
    def __init__(self, preset_json_path=None):
        self.frame_queue = queue.Queue(maxsize=20) # Increased size
        self.range_bins = RANGE_BINS
        if preset_json_path is None:
            preset_json_path = r"C:\RR_02\novelda-uwb-demos\Demos\RadarDirect\X7RadarDirectCallback\Presets\default_preset.json"
        
        self.radar_runner = RadarDirectCallback()
        self._thread = threading.Thread(target=self.radar_runner.run_with_callback_preset, 
                                        args=(self._frame_callback, preset_json_path), daemon=True)
        self._thread.start()
        print("[INFO] X7 PySignalFlow background stream started.")

    def _frame_callback(self, trx_mask, data, seq_num, timestamp, range_offset, bin_length):
        """ Catches the frame. Expected data shape from callback: (2, 2, 192) """
        try:
            frame = np.asarray(data, dtype=np.complex64)
            # Collapse TX dimension: (2, 2, 192) -> (2, 192)
            if frame.ndim == 3:
                frame = np.mean(frame, axis=0) 
            
            # Ensure shape is exactly (2, 192)
            if frame.shape == (2, self.range_bins):
                if not self.frame_queue.full():
                    self.frame_queue.put(frame)
            else:
                print(f"\n[DEBUG] Dropping frame with shape {frame.shape}", end="", flush=True)
        except Exception as e:
            print(f"\n[ERROR] Callback failed: {e}", end="", flush=True)
        return True

    def get_frame(self):
        try: return self.frame_queue.get(timeout=2.0) # Increased timeout
        except queue.Empty: return None

    def close(self): print("[INFO] X7 radar closed.")

# ── RECORDING LOGIC ─────────────────────────────────────────────────────
def record_trial(radar, duration_s, label):
    time.sleep(1.0)
    n_frames = int(duration_s * RADAR_FPS)
    frames = np.zeros((n_frames, 2, RANGE_BINS), dtype=np.complex64)
    collected = 0
    print(f"\n  ▶ Recording '{label}'...", end="")
    while collected < n_frames:
        frame = radar.get_frame()
        if frame is not None:
            frames[collected] = frame
            collected += 1
            print(f"\r  ▶ Recording '{label}' ... {collected}/{n_frames}", end="", flush=True)
        else:
            print(f"\n[WARN] Timeout: No frame received. Check radar connection.", end="", flush=True)
            break
    return frames[:collected]

def run_gesture(args, radar):
    print("\nStarting gesture recording session...")
    choice = input("Enter gesture ID (1-2): ")
    if choice not in GESTURE_CLASSES: return
    folder, desc = GESTURE_CLASSES[choice]
    out_dir = Path(args.out) / folder
    
    data = record_trial(radar, 2.5, desc)
    if len(data) > 0:
        out_dir.mkdir(parents=True, exist_ok=True)
        np.save(out_dir / f"trial_{int(time.time())}.npy", data)
        print(f"\nSaved {len(data)} frames.")

# ── ENTRY POINT ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True)
    parser.add_argument("--out", default="gesture_dataset")
    args = parser.parse_args()
    
    radar = X7Radar()
    try:
        if args.mode == "gesture":
            run_gesture(args, radar)
    finally:
        radar.close()