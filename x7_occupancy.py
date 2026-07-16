"""
x7_occupancy.py
========================
Live human occupancy detection (0 / 1 / 2 people) using the
1D-CNN Keras model trained in Human_sensing_1D_CNN.ipynb.

Usage
-----
  python x7_occupancy.py --model 1d_cnn_human_detection.keras
  python x7_occupancy.py --model 1d_cnn_human_detection.tflite --tflite
"""

import os
os.environ["PATH"] += os.pathsep + r"C:\RR_02\bin"
import argparse
import collections
import time
import sys
import os
import threading
import queue

import numpy as np

# ── SDK import ────────────────────────────────────────────────────────────────
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
WINDOW_SIZE   = 100   # frames per inference window  (must match training)
RANGE_BINS    = 192   # X7F202 native range bins per frame (datasheet Table 1.3)
STRIDE        = 50    # how many new frames before re-inferring
VOTE_WINDOW   = 5     # majority-vote over last N predictions for stability
CLASS_NAMES   = ["0 People", "1 Person", "2 People"]

RADAR_FPS     = 17    
DEPTH_LOWPASS = 0.0   

# ── PREPROCESSING ────────────────────────────────────────────────────────────
def frames_to_magnitude(raw_frames: np.ndarray) -> np.ndarray:
    mag = np.abs(raw_frames.astype(np.complex64))       # (N, 2, 192)
    return np.mean(mag, axis=1).astype(np.float32)       # (N, 192)

def build_window(frame_buffer: np.ndarray) -> np.ndarray:
    w = frame_buffer[-WINDOW_SIZE:].copy()           # (100, 192)
    mean = w.mean()
    std  = w.std() + 1e-8
    w    = (w - mean) / std
    return w[np.newaxis, ...]                        # (1, 100, 192)

# ── MODEL LOADING ─────────────────────────────────────────────────────────────
def load_keras_model(path: str):
    import tensorflow as tf
    model = tf.keras.models.load_model(path)
    print(f"[INFO] Keras model loaded from {path}")
    print(f"       Input  shape : {model.input_shape}")
    print(f"       Output shape : {model.output_shape}")
    return model

def load_tflite_model(path: str):
    import tensorflow as tf
    interpreter = tf.lite.Interpreter(model_path=path)
    interpreter.allocate_tensors()
    inp = interpreter.get_input_details()
    out = interpreter.get_output_details()
    print(f"[INFO] TFLite model loaded from {path}")
    print(f"       Input  shape : {inp[0]['shape']}")
    print(f"       Output shape : {out[0]['shape']}")
    return interpreter, inp, out

def predict_keras(model, window: np.ndarray) -> np.ndarray:
    return model.predict(window, verbose=0)[0]

def predict_tflite(interpreter_bundle, window: np.ndarray) -> np.ndarray:
    interpreter, inp_details, out_details = interpreter_bundle
    interpreter.set_tensor(inp_details[0]['index'], window)
    interpreter.invoke()
    return interpreter.get_tensor(out_details[0]['index'])[0]

# ── SYNTHETIC DATA SOURCE ─────────────────────────────────────────────────────
class SyntheticRadar:
    def __init__(self, fps: int = 17):
        self.fps      = fps
        self.interval = 1.0 / fps

    def __iter__(self):
        while True:
            frame = (np.random.randn(2, RANGE_BINS) +
                     1j * np.random.randn(2, RANGE_BINS)).astype(np.complex64)
            yield frame
            time.sleep(self.interval)

# ── X7 DATA SOURCE ────────────────────────────────────────────────────────────
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
                r"C:\RR_02\novelda-uwb-demos\Demos\RadarDirect\X7BasebandRaw\Presets", 
                "default_preset.json"
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
        frame = np.asarray(data, dtype=np.complex64)
        
        if frame.ndim == 3:
            frame = np.mean(frame, axis=0)  
            
        if frame.shape[1] > self.range_bins:
            frame = frame[:, :self.range_bins]
        elif frame.shape[1] < self.range_bins:
            pad_width = self.range_bins - frame.shape[1]
            frame = np.pad(frame, ((0, 0), (0, pad_width)), mode='constant')

        if not self.frame_queue.full():
            self.frame_queue.put(frame)

    def get_frame(self) -> np.ndarray:
        try:
            return self.frame_queue.get(timeout=0.1)
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

# ── DISPLAY ───────────────────────────────────────────────────────────────────
def display(label: str, probs: np.ndarray, smoothed_label: str):
    bar_width = 30
    lines = [f"\r\033[K  Frame prediction : {label:<12}"]
    for i, (name, p) in enumerate(zip(CLASS_NAMES, probs)):
        filled = int(p * bar_width)
        bar    = "█" * filled + "░" * (bar_width - filled)
        lines.append(f"  {name:<12} [{bar}] {p*100:5.1f}%")
    lines.append(f"  Smoothed (vote)  : \033[1m{smoothed_label}\033[0m")
    print("\033[{}A".format(len(lines) - 1) + "\n".join(lines), end="", flush=True)

# ── MAIN LOOP ─────────────────────────────────────────────────────────────────
def run(args):
    if args.tflite:
        model_bundle = load_tflite_model(args.model)
        infer = lambda w: predict_tflite(model_bundle, w)
    else:
        model = load_keras_model(args.model)
        infer = lambda w: predict_keras(model, w)

    if SDK_AVAILABLE and not args.demo:
        source = X7Radar()
    else:
        print("[INFO] Using synthetic radar data.")
        source = SyntheticRadar(fps=RADAR_FPS)

    mag_buffer    = np.zeros((0, RANGE_BINS), dtype=np.float32)
    vote_deque    = collections.deque(maxlen=VOTE_WINDOW)
    frame_count   = 0
    last_label    = CLASS_NAMES[0]
    last_probs    = np.ones(len(CLASS_NAMES)) / len(CLASS_NAMES)

    print("\n" * (len(CLASS_NAMES) + 2))   
    print("[INFO] Streaming – press Ctrl+C to stop.\n")

    try:
        for raw_frame in source:
            mag_row = frames_to_magnitude(raw_frame[np.newaxis])  
            mag_row = mag_row[0]  
            mag_buffer = np.concatenate([mag_buffer, mag_row[np.newaxis]], axis=0)

            frame_count += 1

            if len(mag_buffer) > WINDOW_SIZE * 3:
                mag_buffer = mag_buffer[-WINDOW_SIZE * 2:]

            if (len(mag_buffer) >= WINDOW_SIZE and
                    (frame_count - WINDOW_SIZE) % STRIDE == 0):

                window      = build_window(mag_buffer)        
                probs       = infer(window)                   
                pred_idx    = int(np.argmax(probs))
                last_label  = CLASS_NAMES[pred_idx]
                last_probs  = probs

                vote_deque.append(pred_idx)
                smoothed_idx   = collections.Counter(vote_deque).most_common(1)[0][0]
                smoothed_label = CLASS_NAMES[smoothed_idx]

                display(last_label, last_probs, smoothed_label)

    except KeyboardInterrupt:
        print("\n\n[INFO] Stopped by user.")
    finally:
        if hasattr(source, 'close'):
            source.close()

# ── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live occupancy detection with X7 + 1D-CNN")
    parser.add_argument("--model",  default="1d_cnn_human_detection.keras",
                        help="Path to .keras or .tflite model file")
    parser.add_argument("--tflite", action="store_true",
                        help="Use TFLite interpreter instead of Keras")
    parser.add_argument("--demo",   action="store_true",
                        help="Force synthetic data even if SDK is present")
    args = parser.parse_args()
    run(args)