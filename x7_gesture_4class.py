"""
x7_gesture.py
======================
Live hand-gesture recognition (12 classes).
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
import torch.nn.functional as F

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
X7_RANGE_BINS  = 96    # Matched to your dataset shape (..., 2, 96)[cite: 2]
X7_WINDOW_SIZE = 64    # Matched to the training window size
VOTE_WINDOW    = 10    # Smooth predictions over 0.25s
GESTURE_FOLDERS = [
    "G01_SWIPE_LR", "G02_SWIPE_RL", "G03_SWIPE_UD", "G04_SWIPE_DU"
]
GESTURE_NAMES  = ["SWIPE_LR", "SWIPE_RL", "SWIPE_UD", "SWIPE_DU"]
N_CLASSES      = len(GESTURE_NAMES)

# ── MODEL DEFINITION ─────────────────────────────────────────────────────────
class GestureCNN_X7(nn.Module):
    def __init__(self, n_classes: int = N_CLASSES):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(4, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(True), nn.MaxPool2d(2),
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
def preprocess_x7native(complex_buffer: np.ndarray) -> torch.Tensor:
    w = complex_buffer[-X7_WINDOW_SIZE:].copy()
    if w.shape[2] > X7_RANGE_BINS: w = w[:, :, :X7_RANGE_BINS]
    
    rx1 = w[:, 0, :]
    rx2 = w[:, 1, :]
    stacked = np.stack([np.real(rx1), np.imag(rx1), np.real(rx2), np.imag(rx2)], axis=0)
    
    mean = np.mean(stacked)
    std = np.std(stacked) + 1e-9
    norm = (stacked - mean) / std
    
    norm = np.transpose(norm, (0, 2, 1))
    return torch.from_numpy(norm).unsqueeze(0).float()

# ── RADAR SOURCE ──────────────────────────────────────────────────────────────
class X7Radar:
    def __init__(self, preset_json_path=None):
        self.frame_queue = queue.Queue(maxsize=50)
        if preset_json_path is None:
            preset_json_path = r"C:\RR_02\novelda-uwb-demos\Demos\RadarDirect\X7RadarDirectCallback\Presets\default_preset.json"
        self.radar_runner = RadarDirectCallback()
        self._thread = threading.Thread(target=self.radar_runner.run_with_callback_preset, args=(self._frame_callback, preset_json_path), daemon=True)
        self._thread.start()
        print("[INFO] Stabilizing stream...")
        time.sleep(2.0)
        
        # Flush the queue to discard startup transients
        while not self.frame_queue.empty():
            self.frame_queue.get_nowait()

    def _frame_callback(self, trx_mask, data, seq_num, timestamp, range_offset, bin_length):
        frame = np.asarray(data, dtype=np.complex64)
        if frame.ndim == 3: frame = np.mean(frame, axis=0)
        if not self.frame_queue.full(): self.frame_queue.put(frame)
        return True

    def get_frame(self) -> np.ndarray:
        try: return self.frame_queue.get(timeout=1.0)
        except queue.Empty: return None

    def __iter__(self):
        while True:
            frame = self.get_frame()
            if frame is not None:
                yield frame

    def close(self): print("[INFO] Radar closed.")

# ── DISPLAY & LOOP ────────────────────────────────────────────────────────────
def display(label, probs, smoothed):
    bar_width = 20
    filled = int(probs[GESTURE_NAMES.index(label)] * bar_width)
    bar = "#" * filled + "-" * (bar_width - filled)
    print(f"\r  {label:<15} [{bar}] {smoothed:<15}", end="", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="best_model_final.pth")
    parser.add_argument("--onnx", action="store_true")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = GestureCNN_X7(n_classes=N_CLASSES).to(device)
    model.load_state_dict(torch.load(args.model, map_location=device))
    model.eval()

    source = X7Radar() if SDK_AVAILABLE else None
    complex_buffer = np.zeros((0, 2, X7_RANGE_BINS), dtype=np.complex64)
    vote_deque = collections.deque(maxlen=VOTE_WINDOW)

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
                complex_row = raw_frame[:, :X7_RANGE_BINS]
                complex_buffer = np.concatenate([complex_buffer, complex_row[np.newaxis]], axis=0)
                
            if len(complex_buffer) > X7_WINDOW_SIZE * 2: 
                complex_buffer = complex_buffer[-X7_WINDOW_SIZE:]
            
            if len(complex_buffer) >= X7_WINDOW_SIZE:
                probs = torch.softmax(model(preprocess_x7native(complex_buffer)), dim=1).detach().cpu().numpy()[0]
                vote_deque.append(probs)
                
                smoothed_probs = np.mean(np.array(vote_deque), axis=0)
                pred_raw = GESTURE_NAMES[int(np.argmax(probs))]
                pred_smooth = GESTURE_NAMES[int(np.argmax(smoothed_probs))]
                
                display(pred_raw, smoothed_probs, pred_smooth)
    except KeyboardInterrupt:
        print("\n[INFO] Stopped.")
    finally:
        if source: source.close()