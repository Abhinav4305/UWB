"""
x7_record.py
=============
Interactive CLI to record labeled training data from the Novelda X7 radar.
Saves .npy files compatible with both:
  - Human_sensing_1D_CNN.ipynb  (occupancy: 0/1/2 people)
  - train_gesture_x7.py         (gesture: 12 classes)

Saved format
------------
Each .npy file: complex64 array, shape (num_frames, 2, 192)
  - num_frames: number of frames recorded
  - 2: number of Rx channels (X7F202 has 1 Tx, 2 Rx)
  - 192: range bins per frame (X7F202 native, datasheet Table 1.3)

Usage
-----
  # Occupancy recording
  python x7_record.py --mode occupancy --out dataset

  # Gesture recording
  python x7_record.py --mode gesture --out gesture_dataset

  # Demo (no radar needed, generates synthetic data)
  python x7_record.py --mode gesture --out gesture_dataset --demo
"""

# ── SDK import ────────────────────────────────────────────────────────────────
import sys
import os # Fixed: Added missing import[cite: 1]
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

import argparse
import time
import threading
import queue
from pathlib import Path
import numpy as np

# Fixed: Defined SDK_AVAILABLE to prevent NameError[cite: 1]
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
    """
    Wraps the official Novelda X7 PySignalFlow SDK using a background thread 
    and a thread-safe queue to route asynchronous frames to a synchronous ML pipeline.
    """
    def __init__(self, port: str = None, preset_json_path=None):
        self.frame_queue = queue.Queue(maxsize=10)
        self.range_bins = RANGE_BINS
        
        if preset_json_path is None:
            preset_json_path = os.path.join(
                r"C:\RR_02\novelda-uwb-demos\Demos\RadarDirect\X7RadarDirectCallback\Presets\default_preset.json"
            )
            
        self.radar_runner = RadarDirectCallback()
        
        self._thread = threading.Thread(
            target=self.radar_runner.run_with_callback_preset,
            args=(self._frame_callback, preset_json_path),
            daemon=True
        )
        self._thread.start()
        print("[INFO] X7 PySignalFlow background stream started.")

    def _frame_callback(self, trx_mask, data, seq_num, timestamp, range_offset, bin_length):
        try:
            frame = np.asarray(data, dtype=np.complex64)
            if frame.ndim == 3:
                frame = np.mean(frame, axis=0)  
            
            # Pad/Truncate logic...
            if frame.shape[1] > self.range_bins:
                frame = frame[:, :self.range_bins]
            elif frame.shape[1] < self.range_bins:
                pad_width = self.range_bins - frame.shape[1]
                frame = np.pad(frame, ((0, 0), (0, pad_width)), mode='constant')

            if not self.frame_queue.full():
                self.frame_queue.put(frame)
        except Exception as e:
            print(f"[ERROR] Callback failed: {e}")
        return True

            
    def get_frame(self) -> np.ndarray:
        try:
            # Increase timeout to wait for the radar to catch up
            return self.frame_queue.get(timeout=1.0) 
        except queue.Empty:
            return None

    def __iter__(self):
        while True:
            frame = self.get_frame()
            if frame is None:
                time.sleep(0.001)
                continue
            
            yield frame

    def close(self):
        print("[INFO] X7 radar closed.")

class SyntheticRadar:
    def get_frame(self) -> np.ndarray:
        time.sleep(1.0 / RADAR_FPS)
        return (np.random.randn(2, RANGE_BINS) +
                1j * np.random.randn(2, RANGE_BINS)).astype(np.complex64)

    def close(self):
        pass

# ── RECORDING ─────────────────────────────────────────────────────────────────
def record_trial(radar, duration_s: float, label: str) -> np.ndarray:
    frames = []
    print(f"\n  ▶ Recording '{label}' for {duration_s:.1f}s ...", end="")

    t_start = time.time()
    while (time.time() - t_start) < duration_s:
        frame = radar.get_frame()
        if frame is not None:
            frames.append(frame)
        # Removed the 'else: sleep' to allow immediate retry
            
        elapsed = time.time() - t_start
        print(f"\r  ▶ Recording '{label}' ... {len(frames)} frames "
              f"({elapsed:.1f}s/{duration_s:.1f}s)", end="", flush=True)

    data = np.array(frames)
    print(f"\r  ✔ Recorded {len(frames)} frames in {time.time()-t_start:.1f}s   ")
    return data

def save_trial(data: np.ndarray, out_dir: Path, subject: str, trial_idx: int):
    out_dir.mkdir(parents=True, exist_ok=True)
    ts       = int(time.time() * 1000)
    filename = f"{subject}_trial_{trial_idx:03d}_{ts}.npy"
    path     = out_dir / filename
    np.save(path, data)
    print(f"  💾 Saved -> {path}  shape={data.shape}")
    return path

def countdown(seconds: int, msg: str = "Starting in"):
    for i in range(seconds, 0, -1):
        print(f"\r  {msg} {i}s ...", end="", flush=True)
        time.sleep(1)
    print(f"\r  {msg} GO!           ")

# ── OCCUPANCY SESSION ─────────────────────────────────────────────────────────
def run_occupancy(args, radar):
    out_root = Path(args.out)
    subject  = args.subject

    print("\n" + "="*55)
    print("  OCCUPANCY RECORDING SESSION")
    print("="*55)
    print("  Classes available:")
    for key, (folder, desc) in OCCUPANCY_CLASSES.items():
        print(f"    [{key}] {desc}")
    print("    [q] Quit")
    print("="*55)

    trial_counters = {k: 1 for k in OCCUPANCY_CLASSES}

    while True:
        print()
        choice = input("  Select class (or q): ").strip()
        if choice.lower() == "q":
            break
        if choice not in OCCUPANCY_CLASSES:
            print("  ✗ Invalid choice.")
            continue

        folder, desc = OCCUPANCY_CLASSES[choice]
        n_trials = int(input(f"  How many trials for '{desc}'? [5]: ") or "5")
        duration = float(input("  Duration per trial (seconds)? [9]: ") or "9")

        for t in range(1, n_trials + 1):
            print(f"\n  — Trial {t}/{n_trials} —")
            input("  Press ENTER when ready, then stay still / set up scene ...")
            countdown(3)
            data = record_trial(radar, duration, desc)
            save_trial(data, out_root / folder, subject,
                       trial_counters[choice])
            trial_counters[choice] += 1

    print("\n[INFO] Occupancy recording session complete.")

# ── GESTURE SESSION ───────────────────────────────────────────────────────────
def run_gesture(args, radar):
    out_root = Path(args.out)
    subject  = args.subject

    print("\n" + "="*55)
    print("  GESTURE RECORDING SESSION")
    print("="*55)
    print("  Gestures available:")
    for key, (folder, desc) in GESTURE_CLASSES.items():
        print(f"    [{key:>2}] {desc}")
    print("    [ q] Quit  |  [all] Record all gestures in sequence")
    print("="*55)
    print(f"\n  Tip: Record 30+ trials per gesture for good model performance.")
    print(f"       Each trial = one gesture execution (~2s).\n")

    trial_counters = {k: 1 for k in GESTURE_CLASSES}
    duration = float(input("  Duration per gesture trial (seconds)? [2.5]: ") or "2.5")
    n_trials = int(input("  Trials per gesture? [30]: ") or "30")

    while True:
        print()
        choice = input("  Select gesture (number / 'all' / q): ").strip().lower()

        if choice == "q":
            break

        if choice == "all":
            keys = list(GESTURE_CLASSES.keys())
        elif choice in GESTURE_CLASSES:
            keys = [choice]
        else:
            print("  ✗ Invalid choice.")
            continue

        for key in keys:
            folder, desc = GESTURE_CLASSES[key]
            reps = n_trials

            print(f"\n  ━━ Gesture: {desc} ━━")
            print(f"     Position yourself in front of the radar.")

            for t in range(1, reps + 1):
                print(f"\n  — Trial {t}/{reps} —")
                input("  Press ENTER, wait for countdown, then perform gesture ...")
                countdown(2, "Gesture in")
                data = record_trial(radar, duration, desc)
                save_trial(data, out_root / folder, subject,
                           trial_counters[key])
                trial_counters[key] += 1

    print("\n[INFO] Gesture recording session complete.")

# ── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="X7 radar data recorder")
    parser.add_argument("--mode",    choices=["occupancy", "gesture"],
                        required=True, help="Recording mode")
    parser.add_argument("--out",     default=None,
                        help="Output dataset root directory")
    parser.add_argument("--subject", default="subject_01",
                        help="Subject/session identifier (used in filenames)")
    parser.add_argument("--port",    default=None,
                        help="Serial port for X7 (e.g. COM3, /dev/ttyUSB0)")
    parser.add_argument("--demo",    action="store_true",
                        help="Use synthetic data (no radar needed)")
    args = parser.parse_args()

    if args.out is None:
        args.out = "dataset" if args.mode == "occupancy" else "gesture_dataset"

    if SDK_AVAILABLE and not args.demo:
        radar = X7Radar(port=args.port)
    else:
        print("[INFO] Demo mode: using synthetic radar data.")
        radar = SyntheticRadar()

    try:
        if args.mode == "occupancy":
            run_occupancy(args, radar)
        else:
            run_gesture(args, radar)
    finally:
        radar.close()