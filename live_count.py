import os
import sys
import argparse
import json
from collections import deque, Counter
import numpy as np

# Suppress TensorFlow logging to keep terminal output clean
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import tensorflow as tf
from tensorflow import keras

# Ensure X7 SDK Bin is on the system path
_X7_SDK_BIN = r"C:\RR_02\X7_SDK_0.6_x64-win\bin"
if _X7_SDK_BIN not in sys.path and os.path.isdir(_X7_SDK_BIN):
    sys.path.insert(0, _X7_SDK_BIN)

# Ensure the callback framework directory is on the path
_CALLBACK_DIR = r"C:\RR_02\novelda-uwb-demos\Demos\RadarDirect\X7RadarDirectCallback"
if _CALLBACK_DIR not in sys.path and os.path.isdir(_CALLBACK_DIR):
    sys.path.insert(0, _CALLBACK_DIR)

from radar_direct_callback import RadarDirectCallback

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WINDOW_SIZE      = 100   # Frames in the sliding window (must match training)
PRED_INTERVAL    = 10    # Run inference every N frames

CONF_THRESHOLD   = 0.75  # Minimum confidence to accept a raw prediction
VOTING_WINDOW    = 15    # Majority-vote history length

STATE_CHANGE_COUNT = 4   # Consecutive agreeing votes required to flip state


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def preprocess_frame(frame):
    """
    Collapse a complex virtual frame to a 1-D range profile feature vector.

    Input shape : (2, 2, 96)  — (TX, RX, range_bins)
    Output shape: (96,)
    """
    frame_mag = np.abs(frame)
    feature   = np.mean(frame_mag, axis=(0, 1))
    return feature


# ---------------------------------------------------------------------------
# Live people counter
# ---------------------------------------------------------------------------

class LivePeopleCounter:
    def __init__(self, model_path):
        print(f"[*] Loading Keras model from: {model_path}")
        self.model = keras.models.load_model(model_path)

        # Model shape sanity check
        print("[*] Model input shape:", self.model.input_shape)
        expected = (None, WINDOW_SIZE, 96)
        if self.model.input_shape != expected:
            print(
                f"[!] WARNING: Expected {expected}, "
                f"got {self.model.input_shape}"
            )

        # Sliding window buffer
        self.buffer      = deque(maxlen=WINDOW_SIZE)
        self.frame_count = 0

        # Prediction stabilization (majority voting)
        self.prediction_history    = deque(maxlen=VOTING_WINDOW)
        self.prev_stable_prediction = 0

        # Occupancy state machine
        self.current_state = 0
        self.pending_state = None
        self.pending_count = 0

        # Motion metric (frame-to-frame feature delta, diagnostic only)
        self.prev_feature = None

        # Frame synchronization
        self.last_tx_data  = [False, False]
        self.virtual_frame = None

    # ------------------------------------------------------------------
    # Radar callback — called by RadarDirectCallback for every TX frame
    # ------------------------------------------------------------------

    def radar_callback(
        self,
        trx_vec,
        radar_data,
        sequence_num,
        timestamp,
        range_offset,
        bin_length,
    ):
        tx_idx = int(trx_vec[1])  # TX channel index: 0 or 1

        # Initialise virtual frame shape on first callback
        if self.virtual_frame is None:
            num_rx, _, num_bins = radar_data.shape
            self.virtual_frame = np.zeros(
                (2, num_rx, num_bins), dtype=np.complex64
            )

        # BBIQ → complex
        complex_data = (
            radar_data[:, 0, :] + 1j * radar_data[:, 1, :]
        ).astype(np.complex64)

        self.virtual_frame[tx_idx, :, :] = complex_data
        self.last_tx_data[tx_idx]        = True

        # Only proceed once both TX channels are populated
        if all(self.last_tx_data):

            feature = preprocess_frame(self.virtual_frame)

            # Reset TX sync flags for the next pair
            self.last_tx_data = [False, False]

            # Motion metric (diagnostic)
            motion = 0.0
            if self.prev_feature is not None:
                motion = float(np.mean(np.abs(feature - self.prev_feature)))
            self.prev_feature = feature

            self.buffer.append(feature)
            self.frame_count += 1

            if self.frame_count % PRED_INTERVAL == 0:
                self.run_inference(motion)

        return True

    # ------------------------------------------------------------------
    # Inference + stabilization + state machine
    # ------------------------------------------------------------------

    def run_inference(self, motion_metric=0.0):
        N = len(self.buffer)

        # Wait until the buffer is full to avoid using padded/cold data
        if N < WINDOW_SIZE:
            sys.stdout.write(f"\rCollecting frames... {N}/{WINDOW_SIZE}   ")
            sys.stdout.flush()
            return

        window = np.array(self.buffer, dtype=np.float32)

        # Global z-score normalisation (matches training pipeline)
        window = (window - np.mean(window)) / (np.std(window) + 1e-8)

        input_data = np.expand_dims(window, axis=0)  # (1, 100, 96)

        predictions = self.model.predict(input_data, verbose=0)[0]
        pred_class  = int(np.argmax(predictions))
        confidence  = float(predictions[pred_class])

        # ---- Confidence gating ----------------------------------------
        if confidence >= CONF_THRESHOLD:
            self.prediction_history.append(pred_class)
            stable_prediction = (
                Counter(self.prediction_history).most_common(1)[0][0]
            )
            self.prev_stable_prediction = stable_prediction
        else:
            # Reject low-confidence frame; hold previous stable vote
            stable_prediction = self.prev_stable_prediction

        # ---- Occupancy state machine -----------------------------------
        if stable_prediction != self.current_state:
            if stable_prediction == self.pending_state:
                self.pending_count += 1
            else:
                self.pending_state = stable_prediction
                self.pending_count = 1

            if self.pending_count >= STATE_CHANGE_COUNT:
                self.current_state = stable_prediction
                self.pending_state = None
                self.pending_count = 0
        else:
            # Stable prediction matches current state — reset pending
            self.pending_state = None
            self.pending_count = 0

        # ---- Console output -------------------------------------------
        labels = ["0 People", "1 Person", "2 People"]

        sys.stdout.write(
            f"\r[FRAME {self.frame_count:5d}] "
            f"State: {labels[self.current_state]:<10} | "
            f"Raw: {labels[pred_class]:<10} | "
            f"Conf: {confidence * 100:5.1f}% | "
            f"Motion: {motion_metric:.4f}   "
        )
        sys.stdout.flush()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Live Radar Inference People Counter"
    )
    parser.add_argument(
        "preset_json",
        nargs="?",
        default="default_preset.json",
        help="Path to the setup preset JSON file",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="1d_cnn_human_detection.keras",
        help="Path to the Keras model file (.keras)",
    )
    parser.add_argument(
        "--playback_file",
        type=str,
        help="Optional playback file for offline validation",
    )
    args = parser.parse_args()

    # Locate model file
    model_path = args.model
    if not os.path.exists(model_path):
        fallback_model = r"C:\RR_02\1d_cnn_human_detection.keras"
        if os.path.exists(fallback_model):
            model_path = fallback_model
        else:
            print(f"Error: Model file '{args.model}' not found.")
            sys.exit(1)

    # Locate preset file
    preset_path = args.preset_json
    if not os.path.exists(preset_path):
        fallback_preset = r"C:\RR_02\default_preset.json"
        if os.path.exists(fallback_preset):
            preset_path = fallback_preset
        else:
            print(f"Error: Preset file '{args.preset_json}' not found.")
            sys.exit(1)

    setup_json = preset_path

    # Playback override (offline validation)
    if args.playback_file:
        print(f"[*] Playback override: using '{args.playback_file}'")
        with open(preset_path, "r") as f:
            preset_data = json.load(f)

        preset_data["IsLive"]       = False
        preset_data["PlaybackFile"] = str(os.path.abspath(args.playback_file))
        preset_data["DoRecording"]  = False

        temp_preset_path = "temp_live_playback_preset.json"
        with open(temp_preset_path, "w") as f:
            json.dump(preset_data, f, indent=4)

        setup_json = temp_preset_path
        print(f"[*] Temporary preset saved to: {temp_preset_path}")

    # Startup banner
    print()
    print("=" * 38)
    print(" LIVE HUMAN OCCUPANCY DETECTION")
    print("=" * 38)
    print(f"Window Size      : {WINDOW_SIZE} frames")
    print(f"Prediction Rate  : every {PRED_INTERVAL} frames")
    print(f"Confidence Gate  : {CONF_THRESHOLD}")
    print(f"Voting Window    : {VOTING_WINDOW} frames")
    print(f"State Change Req : {STATE_CHANGE_COUNT} votes")
    print("=" * 38)
    print()

    counter = LivePeopleCounter(model_path)

    print(f"[*] Starting inference with preset: {setup_json}")
    try:
        RadarDirectCallback().run_with_callback_preset(
            counter.radar_callback,
            setup_json,
        )
    except KeyboardInterrupt:
        print("\n[*] Exiting clean.")
    finally:
        if args.playback_file and os.path.exists("temp_live_playback_preset.json"):
            try:
                os.remove("temp_live_playback_preset.json")
            except Exception:
                pass


if __name__ == "__main__":
    main()