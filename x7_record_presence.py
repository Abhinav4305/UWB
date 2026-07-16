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
RANGE_BINS = 96     # Changed to 96 to match your human sensing model
RADAR_FPS  = 40   

PRESENCE_CLASSES = {
    "0":  ("no_movement/0_people", "0 People (Empty Room)"),
    "1":  ("no_movement/1_people", "1 Person"),
    "2":  ("no_movement/2_people", "2 People"),
}

# ── RADAR SOURCE ────────────────────────────────────────────────────────
class X7Radar:
    def __init__(self, preset_json_path=None):
        self.frame_queue = queue.Queue(maxsize=400) # Increased size
        self.range_bins = RANGE_BINS
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
                
            complex_data = (radar_data[:, 0, :] + 1j * radar_data[:, 1, :]).astype(np.complex64)
            self.virtual_frame[tx_idx, :, :] = complex_data
            self.last_tx_data[tx_idx] = True
            
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
    time.sleep(1.0)
    # Flush any stale frames out of the queue right before we start!
    radar.flush_queue()
    
    n_frames = int(duration_s * RADAR_FPS)
    frames = np.zeros((n_frames, 2, 2, RANGE_BINS), dtype=np.complex64)
    collected = 0
    print(f"\n  ▶ Recording '{label}' for {duration_s} seconds...", end="")
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

def run_presence(args, radar):
    print("\nStarting human presence recording session...")
    
    # 1. Activity Level
    print("Select Activity Level:")
    print("  [0] - No Movement")
    print("  [1] - Movement")
    act_choice = input("Enter choice (0-1): ")
    if act_choice not in ["0", "1"]:
        print("Invalid choice. Defaulting to No Movement.")
        act_choice = "0"
    act_str = "movement" if act_choice == "1" else "no_movement"
    
    # 2. Occupancy
    print("\nSelect Occupancy:")
    print("  [0] - 0 People (Empty Room)")
    print("  [1] - 1 Person")
    print("  [2] - 2 People")
    print("  [3] - 3 People")
    print("  [4] - 4 People")
    print("  [5] - 5 People")
    occ_choice = input("Enter choice (0-5): ")
    if occ_choice not in ["0", "1", "2", "3", "4", "5"]: 
        print("Invalid choice. Defaulting to 1 Person.")
        occ_choice = "1"
    occ_str = f"{occ_choice}_people"
    
    # 3. Duration
    duration_input = input("\nEnter recording duration in seconds (e.g. 10): ")
    try:
        duration_s = float(duration_input)
    except:
        duration_s = 10.0
        
    desc = f"{occ_choice} People ({act_str})"
    out_dir = Path(args.out) / act_str / occ_str
    
    data = record_trial(radar, duration_s, desc)
    if len(data) > 0:
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = f"subject_{int(time.time())}.npy"
        np.save(out_dir / filename, data)
        print(f"\nSaved {len(data)} frames to {out_dir / filename}")

# ── ENTRY POINT ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="presence_dataset")
    args = parser.parse_args()
    
    radar = X7Radar()
    try:
        run_presence(args, radar)
    finally:
        radar.close()
