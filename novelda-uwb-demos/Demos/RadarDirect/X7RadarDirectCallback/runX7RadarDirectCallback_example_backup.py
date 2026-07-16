import sys
import os
import numpy as np

from .radar_direct_callback import RadarDirectCallback

# Class to handle fixed background calibration and subtraction
class RadarProcessor:
    def __init__(self, cal_frames=100):
        self.cal_frames = cal_frames
        self.frame_count = 0
        self.accumulator = None
        self.background = None

    def process(self, x):
        self.frame_count += 1
        
        # Accumulate frames during calibration phase
        if self.frame_count <= self.cal_frames:
            if self.accumulator is None:
                self.accumulator = np.array(x, dtype=complex)
            else:
                self.accumulator += x
            progress = int((self.frame_count / self.cal_frames) * 100)
            return None, f"Calibrating background clutter... {progress}%"
            
        # Calculate the fixed background once calibration is complete
        if self.background is None:
            self.background = self.accumulator / self.cal_frames
            
        # Subtract the static background to reveal the absolute difference
        diff = x - self.background
        return np.abs(diff), None

# Initialize the processor
processor = RadarProcessor(cal_frames=100)

def example_radar_callback(trx_vec: np.ndarray, radar_data: np.ndarray, sequence_num: int, 
                           timestamp: int, range_offset: float, bin_length: float):
    
    # Shape of radar_data is (Tx, Rx, Bins) -> (2, 2, 96)
    # We take Tx 0, Rx 0
    raw_signal = radar_data[0, 0, :]
    num_bins = len(raw_signal)
    
    # Process signal through background subtraction
    dyn_amp, cal_msg = processor.process(raw_signal)
    
    # Rate-limit screen updates to 10 FPS (every 10th frame) to prevent terminal lag and flickering
    if sequence_num % 10 != 0:
        return True
    
    # Calculate physical range vector in meters
    ranges = np.arange(num_bins) * bin_length + range_offset
    
    # Clear terminal screen smoothly
    sys.stdout.write("\033[H\033[J")
    
    sys.stdout.write(f"Seq.Num: {sequence_num} | Timestamp: {timestamp}\n")
    
    if cal_msg is not None:
        sys.stdout.write("=" * 80 + "\n")
        sys.stdout.write(f"STATUS: {cal_msg}\n")
        sys.stdout.write("Please keep the area in front of the radar clear during calibration.\n")
        sys.stdout.write("=" * 80 + "\n")
        sys.stdout.flush()
        return True
        
    sys.stdout.write("Live Radar Profile (Tx 0, Rx 0) - Static Clutter Removed (Fixed Calibration):\n")
    sys.stdout.write("-" * 80 + "\n")
    
    # Draw ASCII plot (taking every 3rd range bin)
    max_dynamic = np.max(dyn_amp) if np.max(dyn_amp) > 0 else 1.0
    for i in range(0, num_bins, 3):
        r = ranges[i]
        dyn_val = dyn_amp[i]
        raw_val = np.abs(raw_signal[i])
        
        # Draw a bar representing the moving amplitude (normalized)
        bar_len = int((dyn_val / max_dynamic) * 40)
        bar = "#" * bar_len
        
        # Only display positive ranges (>0.1m) to filter out near-antenna leakage
        if r >= 0.1:
            sys.stdout.write(f"{r:5.2f} m | Signal: {dyn_val:7.4f} (Raw: {raw_val:7.4f}) | {bar}\n")
            
    sys.stdout.write("-" * 80 + "\n")
    sys.stdout.write("Static environment removed. Place and hold your hand still in front of the radar!\n")
    sys.stdout.write("Restart the script to recalibrate if you move the sensor or change the setup.\n")
    sys.stdout.flush()

    # Return True to continue processing, False to stop the flow
    return True

if __name__ == "__main__":

    if len(sys.argv) > 1:
        setup_json = sys.argv[1]

        RadarDirectCallback().run_with_callback_preset(example_radar_callback, 
            setup_json)

    else:
        print("Usage: python runX7RadarDirectCallback_example.py <path-to-setup.json>")


