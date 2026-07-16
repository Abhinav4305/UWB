import sys
import os
import time
import argparse
import csv
import json
import numpy as np

# Insert SDK binary directory to path
_X7_SDK_BIN = r"C:\RR_02\X7_SDK_0.6_x64-win\bin"
if _X7_SDK_BIN not in sys.path and os.path.isdir(_X7_SDK_BIN):
    sys.path.insert(0, _X7_SDK_BIN)

from radar_direct_callback import RadarDirectCallback

# ====================================================
# Configuration
# ====================================================
DATASET_ROOT = r"c:\RR_02\dataset"

# Global state variables for callback access
trial_frames = []
last_tx_data = [False, False]
virtual_frame = None
target_frames = 0
frame_count = 0

def recording_callback(
    trx_vec: np.ndarray,
    radar_data: np.ndarray,
    sequence_num: int,
    timestamp: int,
    range_offset: float,
    bin_length: float
):
    global trial_frames, last_tx_data, virtual_frame, target_frames, frame_count

    tx_idx = int(trx_vec[1])  # 0 or 1
    num_rx, _, num_bins = radar_data.shape

    # Initialize virtual frame on first callback
    if virtual_frame is None:
        virtual_frame = np.zeros((2, num_rx, num_bins), dtype=np.complex64)

    # Convert current frame from real I/Q to complex
    complex_data = (radar_data[:, 0, :] + 1j * radar_data[:, 1, :]).astype(np.complex64)

    # Update virtual frame slice for the active TX
    virtual_frame[tx_idx, :, :] = complex_data
    last_tx_data[tx_idx] = True

    # Save complex frame once both TX channels have been populated
    if all(last_tx_data):
        trial_frames.append(virtual_frame.copy())
        frame_count += 1
        
        # Print progress bar or ticker
        if frame_count % 20 == 0:
            pct = int((frame_count / target_frames) * 100)
            print(f"Recording: [{'=' * (pct // 10)}{' ' * (10 - pct // 10)}] {pct}% ({frame_count}/{target_frames} frames)", end='\r')

    # Stop flow once target frames are reached
    if frame_count >= target_frames:
        print() # Newline after progress bar
        return False

    return True


def main():
    global trial_frames, last_tx_data, virtual_frame, target_frames, frame_count

    parser = argparse.ArgumentParser(description="Collect Gesture Dataset using Novelda X7 UWB Radar")
    parser.add_argument("preset_json", type=str, help="Path to preset json configuration file")
    parser.add_argument("--gesture", type=str, required=True, help="Name of the gesture (e.g., swipe_left, swipe_right)")
    parser.add_argument("--subject", type=str, required=True, help="Subject identifier (e.g., subject_01)")
    parser.add_argument("--trials", type=int, default=5, help="Number of trials to record")
    parser.add_argument("--duration", type=float, default=2.0, help="Duration of each trial in seconds")
    parser.add_argument("--fps", type=float, default=100.0, help="Target frame rate (frames/second)")
    
    args = parser.parse_args()

    # Ensure dataset paths exist
    gesture_dir = os.path.join(DATASET_ROOT, args.gesture)
    os.makedirs(gesture_dir, exist_ok=True)
    metadata_csv_path = os.path.join(DATASET_ROOT, "metadata.csv")

    # Target number of virtual frames
    target_frames = int(args.duration * args.fps)
    print(f"\n============================================================")
    print(f"GESTURE DATASET COLLECTOR")
    print(f"============================================================")
    print(f"Gesture:   {args.gesture}")
    print(f"Subject:   {args.subject}")
    print(f"Duration:  {args.duration} seconds ({target_frames} frames)")
    print(f"Saving to: {gesture_dir}")
    print(f"============================================================")

    # Initialize metadata CSV if it does not exist
    if not os.path.exists(metadata_csv_path):
        with open(metadata_csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Filename", "Gesture", "Subject", "Trial", "TimestampMs"])

    trial_idx = 1
    while trial_idx <= args.trials:
        print(f"\n------------------------------------------------------------")
        print(f"Trial {trial_idx} of {args.trials} for '{args.gesture}'")
        print(f"------------------------------------------------------------")
        
        user_input = input("Press ENTER when ready to start countdown, or 'q' to quit: ").strip().lower()
        if user_input == 'q':
            print("Exiting collector...")
            break

        # Countdown
        for i in range(3, 0, -1):
            print(f"{i}...")
            time.sleep(1.0)
        print(">>> PERFORM GESTURE NOW! <<<")

        # Reset global state for this trial
        trial_frames = []
        last_tx_data = [False, False]
        virtual_frame = None
        frame_count = 0

        # Start radar streaming for this trial
        try:
            RadarDirectCallback().run_with_callback_preset(
                recording_callback,
                args.preset_json
            )
        except Exception as e:
            print(f"\nError running radar callback: {e}")
            print("Please check connection and try again.")
            continue

        # Save trial data
        if len(trial_frames) >= target_frames:
            timestamp_ms = int(time.time() * 1000)
            filename = f"{args.subject}_trial_{trial_idx:03d}_{timestamp_ms}.npy"
            file_path = os.path.join(gesture_dir, filename)
            
            # Save array as (Frames, TX, RX, Bins)
            arr = np.array(trial_frames)
            np.save(file_path, arr)
            
            # Record in metadata.csv
            with open(metadata_csv_path, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([filename, args.gesture, args.subject, trial_idx, timestamp_ms])
                
            print(f"SUCCESS: Saved {filename}")
            print(f"Array shape: {arr.shape}")
            trial_idx += 1
        else:
            print("WARNING: Capture failed or incomplete. Retrying this trial...")

    print(f"\nDataset collection session complete. Metadata updated at {metadata_csv_path}.")

if __name__ == "__main__":
    main()
