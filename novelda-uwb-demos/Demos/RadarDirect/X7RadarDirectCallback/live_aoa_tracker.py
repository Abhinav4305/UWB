import sys
import os
import csv
import numpy as np
import matplotlib.pyplot as plt

# Insert SDK binary directory to path
_X7_SDK_BIN = r"C:\RR_02\X7_SDK_0.6_x64-win\bin"
if _X7_SDK_BIN not in sys.path and os.path.isdir(_X7_SDK_BIN):
    sys.path.insert(0, _X7_SDK_BIN)

from radar_direct_callback import RadarDirectCallback

# ====================================================
# AOA Beamforming Configuration
# ====================================================
theta_grid = np.linspace(-90, 90, 181)
theta_rad = np.deg2rad(theta_grid)
n = np.array([0, 1, 2])[:, np.newaxis]
steering_vectors = np.exp(+1j * np.pi * n * np.sin(theta_rad))

# ====================================================
# Live Buffers & State variables
# ====================================================
virtual_frame_history = []
last_tx_data = [False, False]

# Peak power threshold to distinguish moving target from static noise floor
# (Adjust this value to tune sensitivity - 500.0 works well for human movement)
POWER_THRESHOLD = 500.0

# Log CSV Configuration
csv_file_path = "live_aoa_log.csv"
csv_file = None
csv_writer = None

# Real-time Plotting setup
plt.ion()
fig, axs = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
rolling_len = 100
time_indices = np.arange(rolling_len)
range_history = np.full(rolling_len, np.nan)
angle_history = np.full(rolling_len, np.nan)

# Line objects for fast updates
line_range, = axs[0].plot(time_indices, range_history, 'b-', lw=2)
line_angle, = axs[1].plot(time_indices, angle_history, 'orange', lw=2)

axs[0].set_title("Real-Time AoA Target Range Tracking")
axs[0].set_ylabel("Range Bin")
axs[0].set_ylim(0, 96)
axs[0].set_xlim(0, rolling_len - 1)
axs[0].grid(True)

axs[1].set_title("Real-Time AoA Target Angle Tracking")
axs[1].set_ylabel("Angle (deg)")
axs[1].set_xlabel("Time Step (Rolling)")
axs[1].set_ylim(-90, 90)
axs[1].grid(True)

fig.tight_layout()

# ====================================================
# Live Callback
# ====================================================
def live_aoa_callback(
    trx_vec: np.ndarray,
    radar_data: np.ndarray,
    sequence_num: int,
    timestamp: int,
    range_offset: float,
    bin_length: float
):
    global virtual_frame_history, last_tx_data, csv_writer
    global range_history, angle_history

    tx_idx = int(trx_vec[1])  # 0 or 1
    num_rx, _, num_bins = radar_data.shape

    # 1. Convert current frame from real I/Q to complex
    complex_data = (radar_data[:, 0, :] + 1j * radar_data[:, 1, :]).astype(np.complex64)

    # 2. Maintain rolling history of virtual frames
    if len(virtual_frame_history) == 0:
        # Initial frame
        current_vf = np.zeros((2, num_rx, num_bins), dtype=np.complex64)
        current_vf[tx_idx, :, :] = complex_data
        virtual_frame_history = [current_vf.copy()] * 3
    else:
        # Get latest state and update active TX slice
        current_vf = virtual_frame_history[0].copy()
        current_vf[tx_idx, :, :] = complex_data
        
        # Roll history
        virtual_frame_history.insert(0, current_vf)
        if len(virtual_frame_history) > 3:
            virtual_frame_history.pop()

    last_tx_data[tx_idx] = True

    # Only process once both TX channels have been populated
    if all(last_tx_data):
        # 3. Apply the 2-step difference filter (current frame - frame from 2 steps ago)
        # This acts as a high-pass filter that preserves alternating TX phase coherence
        V_diff = virtual_frame_history[0] - virtual_frame_history[2]

        # 4. Form the 3-element virtual linear array with phase compensation on TX1 channels
        # Left element: TX0 RX0
        # Middle element: Average of TX0 RX1 and phase-compensated TX1 RX0
        # Right element: Phase-compensated TX1 RX1
        tx0rx0 = V_diff[0, 0, :]
        tx0rx1 = V_diff[0, 1, :]
        tx1rx0 = V_diff[1, 0, :]
        tx1rx1 = V_diff[1, 1, :]

        # Calculate phase difference between TX1RX0 and TX0RX1 (both are middle position)
        Phi = np.angle(tx1rx0 / (tx0rx1 + 1e-9))

        v0 = tx0rx0
        v1 = (tx0rx1 + tx1rx0 * np.exp(-1j * Phi)) / 2.0
        v2 = tx1rx1 * np.exp(-1j * Phi)
        
        V = np.stack([v0, v1, v2], axis=0)        # Shape: (3, num_bins)

        # 5. Compute beamforming
        V_temp = V.T                              # Shape: (num_bins, 3)
        beamformed_signals = np.dot(V_temp, steering_vectors)  # Shape: (num_bins, 181)
        beamformed_power = np.abs(beamformed_signals) ** 2

        # 6. Find target peak in range-angle space
        idx = np.argmax(beamformed_power)
        bin_idx, angle_idx = np.unravel_index(idx, beamformed_power.shape)
        peak_power = beamformed_power[bin_idx, angle_idx]
        angle = theta_grid[angle_idx]

        # Threshold to screen out noise/clutter when no target is present
        is_valid = peak_power > POWER_THRESHOLD

        target_bin = bin_idx if is_valid else np.nan
        target_angle = angle if is_valid else np.nan

        # Append to live plotting history
        range_history[:-1] = range_history[1:]
        range_history[-1] = target_bin
        
        angle_history[:-1] = angle_history[1:]
        angle_history[-1] = target_angle

        # Write to real-time CSV log
        if csv_writer:
            csv_writer.writerow([
                sequence_num, 
                timestamp, 
                target_bin, 
                target_angle, 
                peak_power, 
                "VALID" if is_valid else "NOISE"
            ])

        # Terminal Print
        if is_valid:
            print(f"Frame {sequence_num:5d} | Range Bin: {bin_idx:2d} | Angle: {angle:6.1f}° | Power: {peak_power:8.2f}")
        else:
            if sequence_num % 10 == 0:
                print(f"Frame {sequence_num:5d} | No Target Detected")

        # Update Matplotlib plot (catch TclError if user closed the window)
        try:
            if plt.fignum_exists(fig.number):
                line_range.set_ydata(range_history)
                line_angle.set_ydata(angle_history)
                fig.canvas.draw_idle()
                fig.canvas.flush_events()
        except Exception:
            pass

    return True

# ====================================================
# Main Execution
# ====================================================
if __name__ == "__main__":
    if len(sys.argv) > 1:
        setup_json = sys.argv[1]
    else:
        print("Usage: python live_aoa_tracker.py <path-to-setup.json>")
        sys.exit(1)

    print(f"Opening CSV log file: {csv_file_path}")
    csv_file = open(csv_file_path, "w", newline="")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["SequenceNum", "TimestampMs", "RangeBin", "AngleDeg", "PeakPower", "Status"])

    try:
        # Start streaming radar data with live callback
        RadarDirectCallback().run_with_callback_preset(
            live_aoa_callback,
            setup_json
        )
    except KeyboardInterrupt:
        print("\nStopping Live AoA Tracker...")
    finally:
        csv_file.close()
        print(f"CSV log file saved and closed: {csv_file_path}")
        plt.ioff()
        plt.show()
