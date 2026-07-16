import os
import sys
import argparse
import collections
import json
import numpy as np

# Ensure X7 SDK Bin is on the system path
_X7_SDK_BIN = r"C:\RR_02\X7_SDK_0.6_x64-win\bin"
if _X7_SDK_BIN not in sys.path and os.path.isdir(_X7_SDK_BIN):
    sys.path.insert(0, _X7_SDK_BIN)

import tensorflow as tf
from radar_direct_callback import RadarDirectCallback

class RealTimePeopleCounter:
    def __init__(self, model_path, window_size=100, stride=50, 
                 clutter_mode='window', calibrate_frames=100, smoothing_window=5):
        self.window_size = window_size
        self.stride = stride
        self.clutter_mode = clutter_mode
        self.calibrate_frames = calibrate_frames
        self.smoothing_window = smoothing_window

        # Load TFLite Model
        print(f"[*] Loading TFLite model from: {model_path}")
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        
        # Verify model shape
        expected_shape = self.input_details[0]['shape']
        print(f"[*] Model Input Shape: {expected_shape} | Dtype: {self.input_details[0]['dtype']}")
        assert expected_shape[1] == self.window_size, f"Model expects window size {expected_shape[1]}, but got {self.window_size}."
        self.num_bins = expected_shape[2]
        print(f"[*] Expected Range Bins: {self.num_bins}")

        # Queues and buffers
        self.frame_buffer = collections.deque(maxlen=window_size)
        self.prediction_history = collections.deque(maxlen=smoothing_window)
        
        # Frame sync variables
        self.last_tx_data = [None, None]
        self.virtual_frame = None

        # Counters
        self.total_virtual_frames = 0
        self.new_frames_since_inference = 0

        # Calibration state
        self.calibration_buffer = []
        self.calibrated_background = None
        self.is_calibrating = (clutter_mode == 'calibration')

        print(f"[*] Preprocessing Settings: Clutter Mode = {clutter_mode.upper()} | Stride = {stride}")

    def radar_callback(self, trx_vec, radar_data, sequence_num, timestamp, range_offset, bin_length):
        tx_idx = int(trx_vec[1])  # TX channel: 0 or 1

        # Initialize virtual frame shape dynamically
        if self.virtual_frame is None:
            num_rx, _, num_bins = radar_data.shape
            self.virtual_frame = np.zeros((2, num_rx, num_bins), dtype=np.complex64)

        # Convert raw BBIQ frame to complex representation
        # radar_data has shape (num_rx, 2, num_bins) -> index 0: I, index 1: Q
        complex_data = (radar_data[:, 0, :] + 1j * radar_data[:, 1, :]).astype(np.complex64)

        # Update the virtual frame for the active TX channel
        self.virtual_frame[tx_idx, :, :] = complex_data
        self.last_tx_data[tx_idx] = True

        # Process only when both TX channels have been populated
        if all(self.last_tx_data):
            self.process_virtual_frame(self.virtual_frame)

        return True

    def process_virtual_frame(self, v_frame):
        # 1. Convert complex frame to magnitude
        data_mag = np.abs(v_frame)

        # 2. Average across channels (axis 0: TX, axis 1: RX) for signal stability
        # Output shape: (num_bins,) -> (96,)
        averaged_signal = np.mean(data_mag, axis=(0, 1))

        # Handle calibration mode
        if self.is_calibrating:
            self.calibration_buffer.append(averaged_signal)
            cal_len = len(self.calibration_buffer)
            
            # Print calibration progress
            if cal_len % 10 == 0 or cal_len == self.calibrate_frames:
                print(f"[Calibration] Collected {cal_len}/{self.calibrate_frames} background frames...", end='\r')
                
            if cal_len >= self.calibrate_frames:
                self.calibrated_background = np.mean(self.calibration_buffer, axis=0, keepdims=True)
                self.is_calibrating = False
                print(f"\n[Calibration] Complete! Static clutter background calculated.")
            return

        # Append processed frame to sliding window buffer
        self.frame_buffer.append(averaged_signal)
        self.total_virtual_frames += 1
        self.new_frames_since_inference += 1

        # Check if sliding window is full and stride interval is met
        if len(self.frame_buffer) >= self.window_size and self.new_frames_since_inference >= self.stride:
            self.run_inference()
            self.new_frames_since_inference = 0

    def run_inference(self):
        # Convert frame buffer to numpy array of shape (100, 96)
        window_data = np.array(self.frame_buffer, dtype=np.float32)

        # 1. Clutter Subtraction
        if self.clutter_mode == 'window':
            # Subtract mean of current window along time axis
            window_mean = np.mean(window_data, axis=0, keepdims=True)
            processed_data = window_data - window_mean
        elif self.clutter_mode == 'calibration':
            if self.calibrated_background is not None:
                processed_data = window_data - self.calibrated_background
            else:
                # Fallback to window subtraction if calibration somehow skipped
                window_mean = np.mean(window_data, axis=0, keepdims=True)
                processed_data = window_data - window_mean
        else:
            processed_data = window_data

        # 2. Sample-level normalization: (X - mean) / (std + 1e-8)
        # Note: Mean and standard deviation are computed over the entire 2D matrix
        mean = np.mean(processed_data)
        std = np.std(processed_data) + 1e-8
        normalized_data = (processed_data - mean) / std

        # 3. Reshape for TFLite input: [1, 100, 96]
        input_data = np.expand_dims(normalized_data, axis=0)

        # Run model inference
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])[0]

        # Extract predictions
        predicted_class = int(np.argmax(output_data))
        confidence = float(output_data[predicted_class])

        # Moving average prediction smoothing (majority vote)
        self.prediction_history.append(predicted_class)
        # Calculate majority vote
        counts = collections.Counter(self.prediction_history)
        smoothed_class = counts.most_common(1)[0][0]

        # Draw Terminal UI dashboard
        self.render_ui(predicted_class, confidence, output_data, smoothed_class)

    def render_ui(self, pred_class, confidence, probs, smoothed_class):
        # Clear console screen for a clean refreshing display
        os.system('cls' if os.name == 'nt' else 'clear')

        classes = ['0 People', '1 Person', '2 People']
        icons = ['🈚', '👤', '👥']

        print("=" * 62)
        print("         LIVE PEOPLE COUNTING DASHBOARD (1D-CNN)          ")
        print("=" * 62)
        print(f"  Status:       ACTIVE STREAMING")
        print(f"  Frame Count:  {self.total_virtual_frames} virtual frames")
        print(f"  Clutter Mode: {self.clutter_mode.upper()}")
        print(f"  Stride/Size:  {self.stride} / {self.window_size}")
        print("-" * 62)
        print(f"  PEOPLE COUNT: {icons[smoothed_class]}  \033[1;32m{classes[smoothed_class]}\033[0m")
        print(f"  Raw Prediction: {classes[pred_class]} (Confidence: {confidence:.2%})")
        print("-" * 62)

        # Draw ASCII probability bars
        for i, (name, prob) in enumerate(zip(classes, probs)):
            bar_len = int(prob * 30)
            bar = "█" * bar_len + "░" * (30 - bar_len)
            marker = "◄" if i == smoothed_class else " "
            # Highlight smoothed class row
            if i == smoothed_class:
                print(f"  \033[1;36m{name:<10}\033[0m {marker} [{bar}] {prob:.2%}")
            else:
                print(f"  {name:<10} {marker} [{bar}] {prob:.2%}")

        print("=" * 62)
        print(" Press Ctrl+C to terminate.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real-Time People Counting from Live Radar data using 1D-CNN")
    parser.add_argument("preset_json", help="Path to the setup preset json file")
    parser.add_argument("--model_path", default=r"C:\RR_02\1d_cnn_human_detection.tflite", 
                        help="Path to pre-trained TFLite model file")
    parser.add_argument("--stride", type=int, default=50, help="Sliding window stride (updates every N frames)")
    parser.add_argument("--window_size", type=int, default=100, help="Size of the sliding window buffer")
    parser.add_argument("--clutter_mode", choices=["window", "calibration", "none"], default="window", 
                        help="Clutter subtraction method: 'window' (mean of current window) or 'calibration' (startup average)")
    parser.add_argument("--calibrate_frames", type=int, default=100, 
                        help="Number of initial frames to average for 'calibration' clutter mode")
    parser.add_argument("--smoothing_window", type=int, default=5, 
                        help="History window size for prediction smoothing (majority vote)")
    parser.add_argument("--playback_file", help="Override preset playback file path for off-line playback testing")
    args = parser.parse_args()

    # Load and adjust parameters in preset JSON if playback override is specified
    setup_json = args.preset_json
    
    if args.playback_file:
        print(f"[*] Playback override detected: using '{args.playback_file}'")
        with open(setup_json, 'r') as f:
            preset_data = json.load(f)
        
        # Override fields for playback
        preset_data["IsLive"] = False
        preset_data["PlaybackFile"] = str(os.path.abspath(args.playback_file))
        preset_data["DoRecording"] = False
        
        # Write modified config to a temporary preset json in the local directory
        temp_preset_path = "temp_playback_preset.json"
        with open(temp_preset_path, 'w') as f:
            json.dump(preset_data, f, indent=4)
        
        setup_json = temp_preset_path
        print(f"[*] Temporary configuration saved to: {temp_preset_path}")

    # Initialize processor
    counter = RealTimePeopleCounter(
        model_path=args.model_path,
        window_size=args.window_size,
        stride=args.stride,
        clutter_mode=args.clutter_mode,
        calibrate_frames=args.calibrate_frames,
        smoothing_window=args.smoothing_window
    )

    try:
        # Run Radar callback loop
        RadarDirectCallback().run_with_callback_preset(
            counter.radar_callback,
            setup_json
        )
    except KeyboardInterrupt:
        print("\n[*] Exiting clean.")
    finally:
        # Clean up temporary preset if created
        if args.playback_file and os.path.exists("temp_playback_preset.json"):
            try:
                os.remove("temp_playback_preset.json")
                print("[*] Cleaned up temporary playback configuration.")
            except Exception:
                pass
