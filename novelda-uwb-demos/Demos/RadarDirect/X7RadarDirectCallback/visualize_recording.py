import sys
import os
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# ====================================================
# Main Playback Logic
# ====================================================
def main():
    parser = argparse.ArgumentParser(description="Animate and Visualize recorded Novelda X7 radar baseband files")
    parser.add_argument("npy_file", type=str, help="Path to the recorded .npy file")
    parser.add_argument("--threshold", type=float, default=500.0, help="Power threshold for target detection")
    parser.add_argument("--fps", type=float, default=30.0, help="Playback speed (frames per second)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.npy_file):
        print(f"Error: File not found: {args.npy_file}")
        sys.exit(1)
        
    print(f"Loading recording: {args.npy_file}...")
    try:
        data = np.load(args.npy_file)
    except Exception as e:
        print(f"Error loading file: {e}")
        sys.exit(1)
        
    print(f"Recording Shape: {data.shape}")
    print(f"Recording Dtype: {data.dtype}")
    
    if len(data.shape) != 4 or data.shape[1] != 2 or data.shape[2] != 2:
        print("Error: Expected 4D numpy array with shape (num_frames, 2, 2, num_bins)")
        sys.exit(1)
        
    num_frames, _, _, num_bins = data.shape
    
    # 1. Apply 2-step difference filter (MTI)
    print("Applying difference filter...")
    x_diff = np.zeros_like(data)
    x_diff[2:] = data[2:] - data[:-2]
    
    # 2. Pre-compute Beamforming Maps & Trajectories for high-performance animation
    print("Pre-computing spatial beamforming maps (this will only take a moment)...")
    theta_grid = np.linspace(-90, 90, 181)
    theta_rad = np.deg2rad(theta_grid)
    n = np.array([0, 1, 2])[:, np.newaxis]
    steering_vectors = np.exp(+1j * np.pi * n * np.sin(theta_rad))
    
    bf_maps = np.zeros((num_frames, num_bins, len(theta_grid)))
    track_bins = np.full(num_frames, np.nan)
    track_angles = np.full(num_frames, np.nan)
    track_powers = np.zeros(num_frames)
    
    for f in range(num_frames):
        tx0rx0 = x_diff[f, 0, 0, :]
        tx0rx1 = x_diff[f, 0, 1, :]
        tx1rx0 = x_diff[f, 1, 0, :]
        tx1rx1 = x_diff[f, 1, 1, :]
        
        # Dynamic phase calibration
        Phi = np.angle(tx1rx0 / (tx0rx1 + 1e-9))
        
        v0 = tx0rx0
        v1 = (tx0rx1 + tx1rx0 * np.exp(-1j * Phi)) / 2.0
        v2 = tx1rx1 * np.exp(-1j * Phi)
        
        # Transpose shape (3, num_bins) -> (num_bins, 3)
        V = np.stack([v0, v1, v2], axis=0).T
        
        # Coherent beamforming
        bf = np.dot(V, steering_vectors)
        bf_power = np.abs(bf)**2
        bf_maps[f] = bf_power
        
        # Peak search inside range bins 5 to 50 (ignoring direct coupling near bin 0)
        search_range = bf_power[5:50, :]
        idx = np.argmax(search_range)
        gate_bin_idx, angle_idx = np.unravel_index(idx, search_range.shape)
        actual_bin_idx = gate_bin_idx + 5
        peak_pow = search_range[gate_bin_idx, angle_idx]
        
        track_powers[f] = peak_pow
        if peak_pow > args.threshold:
            track_bins[f] = actual_bin_idx
            track_angles[f] = theta_grid[angle_idx]

    print("Pre-computation complete! Launching visualizer...")
    
    # 3. Setup Plotting Figure
    fig = plt.figure(figsize=(12, 7))
    grid = plt.GridSpec(2, 2, width_ratios=[1.2, 1], wspace=0.3, hspace=0.3)
    
    # Left: Range-Angle Heatmap
    ax_map = fig.add_subplot(grid[:, 0])
    im = ax_map.imshow(
        bf_maps[0].T, 
        aspect='auto', 
        extent=[-90, 90, 0, num_bins - 1], 
        origin='lower', 
        cmap='jet',
        vmax=np.percentile(bf_maps, 99.5) # Color scale auto-scaling
    )
    ax_map.set_title("2D Range-Angle Heatmap")
    ax_map.set_xlabel("Angle (degrees)")
    ax_map.set_ylabel("Range Bin")
    ax_map.set_xlim(-90, 90)
    ax_map.set_ylim(0, 60)
    ax_map.grid(color='white', linestyle='--', alpha=0.3)
    
    # Tracker marker on the heatmap
    marker_target, = ax_map.plot([], [], 'ro', ms=8, mec='white', mew=1.5, label='Target Peak')
    ax_map.legend(loc='upper right')
    
    # Right-Top: Range Bin Tracking History
    ax_range = fig.add_subplot(grid[0, 1])
    line_range_history, = ax_range.plot([], [], 'b-', lw=2, label='Range Bin')
    marker_range_curr, = ax_range.plot([], [], 'bo', ms=6)
    ax_range.set_title("Range Bin Track")
    ax_range.set_ylabel("Bin")
    ax_range.set_xlim(0, num_frames - 1)
    ax_range.set_ylim(0, 60)
    ax_range.grid(True)
    ax_range.legend(loc='upper left')
    
    # Right-Bottom: Angle Tracking History
    ax_angle = fig.add_subplot(grid[1, 1])
    line_angle_history, = ax_angle.plot([], [], 'orange', lw=2, label='Angle (deg)')
    marker_angle_curr, = ax_angle.plot([], [], 'o', color='orange', ms=6)
    ax_angle.set_title("Angle Track")
    ax_angle.set_xlabel("Frame Index")
    ax_angle.set_ylabel("Angle (deg)")
    ax_angle.set_xlim(0, num_frames - 1)
    ax_angle.set_ylim(-90, 90)
    ax_angle.grid(True)
    ax_angle.legend(loc='upper left')
    
    fig.suptitle(f"Playback Visualizer: {os.path.basename(args.npy_file)}", fontsize=14, weight='bold')

    # 4. Animation Update Loop
    def update(frame_idx):
        # Update 2D Heatmap Image
        im.set_data(bf_maps[frame_idx].T)
        
        # Update Target Peak Marker
        curr_bin = track_bins[frame_idx]
        curr_angle = track_angles[frame_idx]
        if not np.isnan(curr_bin):
            marker_target.set_data([curr_angle], [curr_bin])
        else:
            marker_target.set_data([], [])
            
        # Update Range Track History
        # We display the history up to the current frame index
        frames_x = np.arange(frame_idx + 1)
        line_range_history.set_data(frames_x, track_bins[:frame_idx + 1])
        if not np.isnan(curr_bin):
            marker_range_curr.set_data([frame_idx], [curr_bin])
        else:
            marker_range_curr.set_data([], [])
            
        # Update Angle Track History
        line_angle_history.set_data(frames_x, track_angles[:frame_idx + 1])
        if not np.isnan(curr_angle):
            marker_angle_curr.set_data([frame_idx], [curr_angle])
        else:
            marker_angle_curr.set_data([], [])
            
        return im, marker_target, line_range_history, marker_range_curr, line_angle_history, marker_angle_curr

    # Start the animation loop
    interval_ms = int(1000.0 / args.fps)
    ani = animation.FuncAnimation(
        fig, 
        update, 
        frames=num_frames, 
        interval=interval_ms, 
        blit=True, 
        repeat=True
    )
    
    plt.show()

if __name__ == "__main__":
    main()
