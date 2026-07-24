import os
import sys
import time
import queue
import threading
import argparse
import numpy as np
import torch
import torch.nn as nn

# ── SDK IMPORT ────────────────────────────────────────────────────────────────
_DEMO_DIR = r"C:\RR_02\novelda-uwb-demos\Demos\RadarDirect\X7RadarDirectCallback"
if _DEMO_DIR not in sys.path and os.path.isdir(_DEMO_DIR):
    sys.path.insert(0, _DEMO_DIR)

from radar_direct_callback import RadarDirectCallback

# ── CONFIG ────────────────────────────────────────────────────────────────────
X7_RANGE_BINS  = 34    
X7_WINDOW_SIZE = 64    
GESTURE_NAMES  = ["SWIPE_LR", "SWIPE_RL", "SWIPE_UD", "SWIPE_DU", "PUSH_IN"]
N_CLASSES      = len(GESTURE_NAMES)

# ── MODEL DEFINITION ─────────────────────────────────────────────────────────
class GestureCNN_X7_V2(nn.Module):
    def __init__(self, n_classes=N_CLASSES):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(8, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(128, 256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(256, 512, 3, padding=1), nn.BatchNorm2d(512), nn.ReLU(True),
            nn.AdaptiveAvgPool2d((4, 4)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(), nn.Linear(512 * 16, 512), nn.ReLU(True), nn.Dropout(0.4),
            nn.Linear(512, 128), nn.ReLU(True), nn.Dropout(0.3), nn.Linear(128, n_classes),
        )
    def forward(self, x): 
        return self.classifier(self.features(x))

def preprocess_buffer(complex_buffer: np.ndarray) -> torch.Tensor:
    # We only take the last 64 frames
    w = complex_buffer[-X7_WINDOW_SIZE:]
    
    # Extract 8 channels (Real and Imag for all 4 TX/RX pairs)
    stacked = np.stack([
        np.real(w[:, 0, 0, :]), np.imag(w[:, 0, 0, :]),
        np.real(w[:, 0, 1, :]), np.imag(w[:, 0, 1, :]),
        np.real(w[:, 1, 0, :]), np.imag(w[:, 1, 0, :]),
        np.real(w[:, 1, 1, :]), np.imag(w[:, 1, 1, :])
    ], axis=0)
    
    # MTI: Subtract time-mean
    stacked = stacked - np.mean(stacked, axis=1, keepdims=True)
    
    # Z-Score Normalization
    stacked = (stacked - np.mean(stacked)) / (np.std(stacked) + 1e-9)
    
    # Format for PyTorch: (Batch=1, Channels=8, Bins=34, Time=64)
    tensor = torch.from_numpy(np.transpose(stacked, (0, 2, 1))).unsqueeze(0).float()
    return tensor

# ── RADAR INTERFACE ──────────────────────────────────────────────────────────
class X7RadarLive:
    def __init__(self):
        self.frame_queue = queue.Queue(maxsize=1000)
        self.virtual_frame = np.zeros((2, 2, X7_RANGE_BINS), dtype=np.complex64)
        self.tx_flags = [False, False]
        
        preset = r"C:\RR_02\novelda-uwb-demos\Demos\RadarDirect\X7RadarDirectCallback\Presets\default_preset.json"
        
        self.runner = RadarDirectCallback()
        self.thread = threading.Thread(
            target=self.runner.run_with_callback_preset, 
            args=(self._callback, preset), 
            daemon=True
        )
        self.thread.start()
        
        print("[INFO] Waiting for radar stream to stabilize...")
        time.sleep(2.0)
        
        # Flush initial noise
        while not self.frame_queue.empty():
            self.frame_queue.get()

    def _callback(self, trx_mask, data, seq_num, timestamp, range_offset, bin_length):
        try:
            tx = int(trx_mask[1])
            raw = np.asarray(data, dtype=np.float32)
            
            # Combine I and Q into complex numbers, truncate bins
            complex_raw = (raw[:, 0, :X7_RANGE_BINS] + 1j * raw[:, 1, :X7_RANGE_BINS]).astype(np.complex64)
            
            self.virtual_frame[tx, :, :] = complex_raw
            self.tx_flags[tx] = True
            
            # When we have both TX0 and TX1, we have a complete 2x2 MIMO frame
            if self.tx_flags[0] and self.tx_flags[1]:
                if not self.frame_queue.full():
                    self.frame_queue.put(self.virtual_frame.copy())
                self.tx_flags = [False, False]
        except Exception:
            pass
        return True
        
    def close(self):
        print("\n[INFO] Radar stream closed.")

# ── MAIN LIVE INFERENCE LOOP ────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/best_model_1m_aug.pth")
    parser.add_argument("--energy", type=float, default=150.0, help="Minimum energy to trigger inference")
    parser.add_argument("--threshold", type=float, default=0.65, help="Confidence required to trigger detection")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    print("[INFO] Loading neural network...")
    model = GestureCNN_X7_V2().to(device)
    model.load_state_dict(torch.load(args.model, map_location=device))
    model.eval()

    radar = X7RadarLive()
    buffer = np.zeros((0, 2, 2, X7_RANGE_BINS), dtype=np.complex64)
    
    cooldown = 0
    
    print("\n" + "="*50)
    print(" LIVE GESTURE DETECTION (RAW PROBABILITY MODE)")
    print("="*50)
    print("Waiting for gestures...\n")

    try:
        while True:
            # 1. Drain the queue to stay in real-time
            frames = []
            while not radar.frame_queue.empty():
                frames.append(radar.frame_queue.get())
                
            if not frames:
                time.sleep(0.01)
                continue
                
            # 2. Add new frames to the sliding window buffer
            for f in frames:
                buffer = np.concatenate([buffer, f[np.newaxis]], axis=0)
                if cooldown > 0:
                    cooldown -= 1
                    
            if len(buffer) > X7_WINDOW_SIZE:
                buffer = buffer[-X7_WINDOW_SIZE:]
                
            # 3. Only evaluate if we have a full window and aren't in cooldown
            if len(buffer) == X7_WINDOW_SIZE and cooldown == 0:
                # Calculate MTI energy across the window
                mti = buffer - np.mean(buffer, axis=0, keepdims=True)
                energy = np.max(np.sum(np.abs(mti), axis=(1, 2, 3)))
                
                # Check if someone is moving
                if energy > args.energy:
                    # Run inference directly on the raw probabilities (NO EMA SMOOTHING)
                    tensor = preprocess_buffer(buffer).to(device)
                    with torch.no_grad():
                        probs = torch.softmax(model(tensor), dim=1)[0].cpu().numpy()
                        
                    max_prob = np.max(probs)
                    pred_idx = np.argmax(probs)
                    
                    # If the model is confident enough, trigger it
                    if max_prob >= args.threshold:
                        gesture = GESTURE_NAMES[pred_idx]
                        print(f"[{time.strftime('%H:%M:%S')}] >> GESTURE DETECTED: {gesture:<12} (Confidence: {max_prob*100:.1f}%, Energy: {energy:.1f})")
                        
                        # Set a 40 frame (1 second) cooldown to drop frames while hand returns
                        cooldown = 80
                        # Clear the buffer so the return-movement doesn't get evaluated
                        buffer = np.zeros((0, 2, 2, X7_RANGE_BINS), dtype=np.complex64)
                
    except KeyboardInterrupt:
        pass
    finally:
        radar.close()
