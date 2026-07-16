"""
x7_gesture_4class_v2.py
======================
Live hand-gesture recognition (4 classes) using the V2 8-channel model.
"""

import os
import argparse
import collections
import time
import sys
import threading
import queue
import numpy as np
import torch
import torch.nn as nn

# ── SDK IMPORT ────────────────────────────────────────────────────────────────
_DEMO_DIR = r"C:\RR_02\novelda-uwb-demos\Demos\RadarDirect\X7RadarDirectCallback"
if _DEMO_DIR not in sys.path and os.path.isdir(_DEMO_DIR):
    sys.path.insert(0, _DEMO_DIR)

try:
    from radar_direct_callback import RadarDirectCallback
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    print("[WARN] Novelda SDK/Callback not found – running in DEMO mode.")

# ── CONFIG ────────────────────────────────────────────────────────────────────
X7_RANGE_BINS  = 96    
X7_WINDOW_SIZE = 64    
VOTE_WINDOW    = 5    
GESTURE_NAMES  = ["SWIPE_LR", "SWIPE_RL", "SWIPE_UD", "SWIPE_DU"]
N_CLASSES      = len(GESTURE_NAMES)

# ── MODEL DEFINITION ─────────────────────────────────────────────────────────
class GestureCNN_X7_V2(nn.Module):
    def __init__(self, n_classes: int = N_CLASSES):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(8, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(128, 256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(True),
            nn.AdaptiveAvgPool2d((4, 4)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(256 * 16, 512), nn.ReLU(True), nn.Dropout(0.4),
            nn.Linear(512, 128), nn.ReLU(True), nn.Dropout(0.3),
            nn.Linear(128, n_classes),
        )
    def forward(self, x): return self.classifier(self.features(x))

# ── PREPROCESSING ─────────────────────────────────────────────────────────────
def preprocess_x7native_v2(complex_buffer: np.ndarray) -> torch.Tensor:
    # complex_buffer shape: (64, 2, 2, 96) complex64
    w = complex_buffer[-X7_WINDOW_SIZE:].copy()
    if w.shape[3] > X7_RANGE_BINS: w = w[:, :, :, :X7_RANGE_BINS]
    
    tx0_rx0 = w[:, 0, 0, :]
    tx0_rx1 = w[:, 0, 1, :]
    tx1_rx0 = w[:, 1, 0, :]
    tx1_rx1 = w[:, 1, 1, :]
    
    stacked = np.stack([
        np.real(tx0_rx0), np.imag(tx0_rx0),
        np.real(tx0_rx1), np.imag(tx0_rx1),
        np.real(tx1_rx0), np.imag(tx1_rx0),
        np.real(tx1_rx1), np.imag(tx1_rx1)
    ], axis=0)
    
    # MTI Filter: Remove static background by subtracting the time-mean
    time_mean = np.mean(stacked, axis=1, keepdims=True)
    stacked = stacked - time_mean
    
    mean = np.mean(stacked)
    std = np.std(stacked)
    norm = (stacked - mean) / (std + 1e-9)
    
    norm = np.transpose(norm, (0, 2, 1))
    return torch.from_numpy(norm).unsqueeze(0).float(), std

# ── RADAR SOURCE ──────────────────────────────────────────────────────────────
class X7Radar:
    def __init__(self, preset_json_path=None):
        self.frame_queue = queue.Queue(maxsize=400)
        self.range_bins = X7_RANGE_BINS
        self.virtual_frame = np.zeros((2, 2, X7_RANGE_BINS), dtype=np.complex64)
        self.last_tx_data = [False, False]
        
        if preset_json_path is None:
            preset_json_path = r"C:\RR_02\novelda-uwb-demos\Demos\RadarDirect\X7RadarDirectCallback\Presets\default_preset.json"
        
        self.radar_runner = RadarDirectCallback()
        self._thread = threading.Thread(target=self.radar_runner.run_with_callback_preset, 
                                        args=(self._frame_callback, preset_json_path), daemon=True)
        self._thread.start()
        print("[INFO] Stabilizing stream...")
        time.sleep(2.0)
        
        while not self.frame_queue.empty():
            self.frame_queue.get_nowait()

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

    def flush_queue(self):
        while not self.frame_queue.empty():
            try: self.frame_queue.get_nowait()
            except: break

    def close(self): print("[INFO] Radar closed.")

# ── DISPLAY & LOOP ────────────────────────────────────────────────────────────
def display(label, probs=None, smoothed=""):
    bar_width = 20
    if probs is None or label == "IDLE":
        bar = "-" * bar_width
    else:
        try:
            filled = int(probs[GESTURE_NAMES.index(label)] * bar_width)
            bar = "#" * filled + "-" * (bar_width - filled)
        except ValueError:
            bar = "?" * bar_width
    print(f"\r  {label:<15} [{bar}] {smoothed:<15}", end="", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/best_model_4class_v2.pth")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = GestureCNN_X7_V2(n_classes=N_CLASSES).to(device)
    
    if not os.path.exists(args.model):
        print(f"[ERROR] Could not find model: {args.model}")
        sys.exit(1)
        
    model.load_state_dict(torch.load(args.model, map_location=device))
    model.eval()

    source = X7Radar() if SDK_AVAILABLE else None
    complex_buffer = np.zeros((0, 2, 2, X7_RANGE_BINS), dtype=np.complex64)
    frame_counter = 0
    cooldown_frames = 0
    prediction_history = collections.deque(maxlen=VOTE_WINDOW)

    try:
        while True:
            # Drain all available frames from the queue to stay in real-time
            frames_batch = []
            while not source.frame_queue.empty():
                frames_batch.append(source.frame_queue.get())
                
            if not frames_batch:
                time.sleep(0.01)
                continue
                
            for raw_frame in frames_batch:
                complex_row = raw_frame[:, :, :X7_RANGE_BINS]
                complex_buffer = np.concatenate([complex_buffer, complex_row[np.newaxis]], axis=0)
                frame_counter += 1
                if cooldown_frames > 0:
                    cooldown_frames -= 1
                
            # Limit buffer to window size to prevent memory leaks
            if len(complex_buffer) > X7_WINDOW_SIZE: 
                complex_buffer = complex_buffer[-X7_WINDOW_SIZE:]
            
            # Evaluate every 2 frames (approx 0.05 seconds) for snappy response!
            if len(complex_buffer) == X7_WINDOW_SIZE and frame_counter >= 2:
                frame_counter = 0
                
                if cooldown_frames > 0:
                    display("IDLE", None, "(Cooldown)")
                    continue
                
                # Step 1: Energy check to ignore empty rooms (Using MTI to remove static background)
                # We check the ENTIRE window so the model evaluates the gesture as it slides through the sweet spot!
                mti_buffer = complex_buffer - np.mean(complex_buffer, axis=0, keepdims=True)
                frame_energy = np.sum(np.abs(mti_buffer), axis=(1, 2, 3))
                
                if np.max(frame_energy) < 180:
                    display("IDLE", None)
                    prediction_history.clear()
                    continue
                
                # Step 2: Evaluate Model
                tensor, _ = preprocess_x7native_v2(complex_buffer)
                probs = torch.softmax(model(tensor), dim=1).detach().cpu().numpy()[0]
                pred_idx = int(np.argmax(probs))
                pred_raw = GESTURE_NAMES[pred_idx]
                confidence = probs[pred_idx]
                
                # Step 3: Vote!
                if confidence > 0.85:
                    prediction_history.append(pred_raw)
                else:
                    prediction_history.append("UNKNOWN")
                    
                if len(prediction_history) == VOTE_WINDOW:
                    counts = collections.Counter(prediction_history)
                    most_common, count = counts.most_common(1)[0]
                    
                    # If 3 out of 3 (or 4 out of 5) frames agree, it's a REAL gesture!
                    if most_common != "UNKNOWN" and count >= VOTE_WINDOW - 1:
                        print("\r" + " "*60, end="\r") # Clear line
                        print(f"\n>> GESTURE DETECTED: {most_common} (Voted!) <<\n")
                        cooldown_frames = 40
                        prediction_history.clear()
                        continue
                
                display(pred_raw if confidence > 0.85 else "IDLE", probs, f"Vote: {len(prediction_history)}/{VOTE_WINDOW}")
                    
    except KeyboardInterrupt:
        print("\n[INFO] Stopped.")
    finally:
        if source: source.close()

