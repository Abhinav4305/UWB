import sys
import numpy as np

from radar_direct_callback import RadarDirectCallback

# ====================================================
# Recording Settings
# ====================================================

MAX_FRAMES = 1000
all_frames = []
all_frames_bbiq = []

# Caches to track the alternating TX channels
last_tx_data = [None, None]
virtual_frame = None

# ====================================================
# Callback
# ====================================================

def example_radar_callback(
    trx_vec: np.ndarray,
    radar_data: np.ndarray,
    sequence_num: int,
    timestamp: int,
    range_offset: float,
    bin_length: float
):

    global all_frames, all_frames_bbiq, virtual_frame, last_tx_data

    # Save raw BBIQ frame as backup
    all_frames_bbiq.append(radar_data.copy())

    tx_idx = int(trx_vec[1])  # 0 or 1

    # Initialize virtual_frame dynamically based on radar_data shape
    if virtual_frame is None:
        num_rx, _, num_bins = radar_data.shape
        virtual_frame = np.zeros((2, num_rx, num_bins), dtype=np.complex64)

    # Convert current frame from real I/Q to complex
    # radar_data has shape (num_rx, 2, num_bins) -> index 0: I, index 1: Q
    complex_data = (radar_data[:, 0, :] + 1j * radar_data[:, 1, :]).astype(np.complex64)

    # Update virtual frame slice for the active TX
    virtual_frame[tx_idx, :, :] = complex_data
    last_tx_data[tx_idx] = True

    # Print info once
    if sequence_num == 1:

     print("radar_data shape:", radar_data.shape)
     print("radar_data dtype:", radar_data.dtype)

     print("First channel first 20 samples:")
     print(radar_data[0,0,:20])

     input("\nPress Enter to continue...")

    # Save virtual complex frame only after both TX channels have been populated
    if all(last_tx_data):
        all_frames.append(virtual_frame.copy())

    # Progress update every 100 frames
    if len(all_frames) % 100 == 0 and len(all_frames) > 0:
        print(f"Captured {len(all_frames)} / {MAX_FRAMES} frames")

    # Save and stop
    if len(all_frames) >= MAX_FRAMES:

        arr_complex = np.array(all_frames)
        arr_bbiq = np.array(all_frames_bbiq)

        print("\n===== RECORDING COMPLETE =====")
        print("Final Complex Shape:", arr_complex.shape)
        print("Complex Data Type  :", arr_complex.dtype)
        print("Final BBIQ Shape   :", arr_bbiq.shape)
        print("BBIQ Data Type      :", arr_bbiq.dtype)

        np.save("recording.npy", arr_complex)
        np.save("recording_bbiq.npy", arr_bbiq)

        print("Saved file: recording.npy")
        print("Saved file: recording_bbiq.npy")
        print("==============================")

        return False

    return True

# ====================================================
# Main
# ====================================================

if __name__ == "__main__":

    if len(sys.argv) > 1:

        setup_json = sys.argv[1]

        RadarDirectCallback().run_with_callback_preset(
            example_radar_callback,
            setup_json
        )

    else:
        print(
            "Usage: python runX7RadarDirectCallback_example.py <path-to-setup.json>"
        )