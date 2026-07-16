"""
x7_record.py
=============
Interactive CLI to record labeled training data from the Novelda X7 radar.
"""

import sys
import os
import argparse
import time
import threading
import queue
from pathlib import Path
import numpy as np

# ── SDK IMPORT ────────────────────────────────────────────────────────────────
_DEMO_DIR = r"C:\RR_02\novelda-uwb-demos\Demos\RadarDirect\X7RadarDirectCallback"
_DEMO_PARENT = r"C:\RR_02\novelda-uwb-demos\Demos"
for path in [_DEMO_PARENT, _DEMO_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

_SDK_BIN = r"C:\RR_02\X7_SDK_0.6_x64-win\bin"
if _SDK_BIN not in sys.path:
    sys.path.insert(0, _SDK_BIN)
if hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(_SDK_BIN)

try:
    from radar_direct_callback import RadarDirectCallback
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

# ── HARDWARE CONFIG ───────────────────────────────────────────────────────────
RANGE_BINS = 192    
RADAR_FPS  = 40  

# ── CLASS DEFINITIONS ─────────────────────────────────────────────────────────
OCCUPANCY_CLASSES = {
    "0": ("no_movement/0_people", "0 people – stationary"),
    "1": ("no_movement/1_people", "1 person  – stationary"),
    "2": ("no_movement/2_people", "2 people  – stationary"),
    "3": ("movement/0_people",    "0 people  – moving objects"),
    "4": ("movement/1_people",    "1 person  – moving"),
    "5": ("movement/2_people",    "2 people  – moving"),
}

GESTURE_CLASSES = {
    "1":  ("G01_SWIPE_LR",      "Left -> Right swipe"),
    "2":  ("G02_SWIPE_RL",      "Right -> Left swipe"),
    "3":  ("G03_SWIPE_UD",      "Up -> Down swipe"),
    "4":  ("G04_SWIPE_DU",      "Down -> Up swipe"),
    "5":  ("G05_DIAG_LR_UD",   "Diagonal LR-UD"),
    "6":  ("G06_DIAG_LR_DU",   "Diagonal LR-DU"),
    "7":  ("G07_DIAG_RL_UD",   "Diagonal RL-UD"),
    "8":  ("G08_DIAG_RL_DU",   "Diagonal RL-DU"),
    "9":  ("G09_CLOCKWISE",     "Clockwise circle"),
    "10": ("G10_ANTICLOCKWISE", "Anti-clockwise circle"),
    "11": ("G11_INWARD_PUSH",   "Inward push"),
    "12": ("G12_EMPTY",         "Empty / no gesture"),
}

# ── RADAR SOURCE ──────────────────────────────────────────────────────────────
class X7Radar:
    def __init__(self, port: str = None, preset_json_path=None):
        self.frame_queue = queue.Queue(maxsize=50)
        self.range_bins = RANGE_BINS
        
        if preset_json_path is None:
            preset_json_path = r"C:\RR_02\novelda-uwb-demos\Demos\RadarDirect\X7RadarDirectCallback\Presets\default_preset.json"
            
        self.radar_runner = RadarDirectCallback()
        self._thread = threading.Thread(
            target=self.radar_runner.run_with_callback_preset,
            args=(self._frame_callback, preset_json_path),
            daemon=True
        )
        self._thread.start()
        
        print("[INFO] Waiting for radar stream to stabilize...", end="", flush=True)
        for _ in range(20):
            if not self.frame_queue.empty():
                print(" LIVE.")
                return
            time.sleep(0.5)
            print(".", end="", flush=True)
        print("\n[WARNING] Radar stream took too long to start.")

    def _frame_callback(self, trx_mask, data, seq_num, timestamp, range_offset, bin_length):
        try:
            frame = np.asarray(data, dtype=np.complex64)
            if frame.ndim == 3: frame = np.mean(frame, axis=0)  
            if frame.shape[1] > self.range_bins: frame = frame[:, :self.range_bins]
            if not self.frame_queue.full(): self.frame_queue.put(frame)
        except Exception as e:
            print(f"[ERROR] Callback failed: {e}")
        return True

    def get_frame(self) -> np.ndarray:
        try: return self.frame_queue.get(timeout=1.0) 
        except queue.Empty: return None

    def close(self): print("[INFO] X7 radar closed.")

class SyntheticRadar:
    def get_frame(self) -> np.ndarray:
        time.sleep(1.0 / RADAR_FPS)
        return (np.random.randn(2, RANGE_BINS) + 1j * np.random.randn(2, RANGE_BINS)).astype(np.complex64)
    def close(self): pass

# ── RECORDING ─────────────────────────────────────────────────────────────────
def record_trial(radar, duration_s: float, label: str) -> np.ndarray:
    while not radar.frame_queue.empty(): radar.frame_queue.get_nowait()
    frames = []
    print(f"\n  ▶ Recording '{label}' for {duration_s:.1f}s ...", end="")
    t_start = time.time()
    while (time.time() - t_start) < duration_s:
        frame = radar.get_frame()
        if frame is not None: frames.append(frame)
        time.sleep(0.01)
    
    data = np.array(frames)
    print(f"\r  ✔ Recorded {len(frames)} frames in {time.time()-t_start:.1f}s")
    return data

def save_trial(data, out_dir, subject, trial_idx):
    # Fixed Path creation using Path objects to prevent double separators[cite: 2]
    full_path = Path(out_dir) / f"{subject}_trial_{trial_idx:03d}_{int(time.time() * 1000)}.npy"
    full_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(full_path, data)
    print(f"  💾 Saved -> {full_path} | Shape: {data.shape}")

def countdown(seconds: int, msg: str = "Starting in"):
    for i in range(seconds, 0, -1):
        print(f"\r  {msg} {i}s ...", end="", flush=True)
        time.sleep(1)
    print(f"\r  {msg} GO!           ")

def run_gesture(args, radar):
    out_root = Path(args.out)
    subject  = args.subject
    trial_counters = {k: 1 for k in GESTURE_CLASSES}
    duration = float(input("  Duration per gesture trial (seconds)? [2.5]: ") or "2.5")
    n_trials = int(input("  Trials per gesture? [30]: ") or "30")

    while True:
        choice = input("\n  Select gesture (number / 'all' / q): ").strip().lower()
        if choice == "q": break
        keys = list(GESTURE_CLASSES.keys()) if choice == "all" else ([choice] if choice in GESTURE_CLASSES else [])
        if not keys: continue

        for key in keys:
            folder, desc = GESTURE_CLASSES[key]
            for t in range(1, n_trials + 1):
                try:
                    input(f"\n  — Trial {t}/{n_trials} — Press ENTER to start ...")
                    countdown(2, "Gesture in")
                    data = record_trial(radar, duration, desc)
                    save_trial(data, out_root / folder, subject, trial_counters[key])
                    trial_counters[key] += 1
                except Exception as e:
                    print(f"\n[ERROR] Trial {t} failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["occupancy", "gesture"], required=True)
    parser.add_argument("--out", default="gesture_dataset")
    parser.add_argument("--subject", default="subject_01")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    radar = X7Radar() if (SDK_AVAILABLE and not args.demo) else SyntheticRadar()
    try: 
        if args.mode == "gesture": run_gesture(args, radar)
        else: print("Occupancy mode needs implementation")
    finally: radar.close()