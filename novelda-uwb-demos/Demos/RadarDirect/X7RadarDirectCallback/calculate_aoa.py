import numpy as np
import matplotlib.pyplot as plt


# =====================================================
# LOAD DATA
# =====================================================

movement = np.load("rightmovement_bbiq.npy")
no_movement = np.load("no_movement.npy")

print("Movement shape:", movement.shape)
print("No Movement shape:", no_movement.shape)

# Use same number of frames
num_frames = min(
    movement.shape[0],
    no_movement.shape[0]
)

movement = movement[:num_frames]
no_movement = no_movement[:num_frames]

print("Global min:", np.min(movement))
print("Global max:", np.max(movement))

print("Unique dtype:", movement.dtype)
print("Any complex:", np.iscomplexobj(movement))

print("dtype:", movement.dtype)
print("shape:", movement.shape)

print("sample frame shape:", movement[0].shape)
print("channel shape:", movement[0,0,0].shape)

print("First 10 values:")
print(movement[0,0,0,:10])

# Background subtraction
x = movement - no_movement

frame = 500
bin_idx = 25

print(
    "Mean channel powers:",
    np.mean(np.abs(x[:,0,0,:])),
    np.mean(np.abs(x[:,0,1,:])),
    np.mean(np.abs(x[:,1,0,:])),
    np.mean(np.abs(x[:,1,1,:]))
)

print("\nChannel values:")
print("TX0RX0 =", x[frame,0,0,bin_idx])
print("TX0RX1 =", x[frame,0,1,bin_idx])
print("TX1RX0 =", x[frame,1,0,bin_idx])
print("TX1RX1 =", x[frame,1,1,bin_idx])

print("Movement max:", np.max(np.abs(movement)))
print("No movement max:", np.max(np.abs(no_movement)))
print("Difference max:", np.max(np.abs(x)))

print("Processed shape:", x.shape)

num_frames, num_tx, num_rx, num_bins = x.shape


# =====================================================
# BUILD VIRTUAL ARRAY & APPLY HIGH-PASS FILTER
# =====================================================

# A 2-step difference filter (x[t] - x[t-2]) acts as a high-pass filter
# and preserves phase coherence for the alternating TX channels
x_diff = np.zeros_like(x)
x_diff[2:] = x[2:] - x[:-2]

# Extract individual difference channels
tx0rx0 = x_diff[:, 0, 0, :]  # Left
tx0rx1 = x_diff[:, 0, 1, :]  # Middle (TX0)
tx1rx0 = x_diff[:, 1, 0, :]  # Middle (TX1)
tx1rx1 = x_diff[:, 1, 1, :]  # Right

# Calculate phase difference between TX1RX0 and TX0RX1 (both are middle position)
Phi = np.angle(tx1rx0 / (tx0rx1 + 1e-9))

# Form phase-compensated 3-element virtual linear array [left, middle, right]
v0 = tx0rx0
v1 = (tx0rx1 + tx1rx0 * np.exp(-1j * Phi)) / 2.0
v2 = tx1rx1 * np.exp(-1j * Phi)

# Shape = (3, Frames, Bins)
V_clean = np.stack([v0, v1, v2], axis=0)

print("Virtual array shape:", V_clean.shape)


# =====================================================
# BEAMFORMING SETUP
# =====================================================

theta_grid = np.linspace(
    -90,
    90,
    181
)

theta_rad = np.deg2rad(
    theta_grid
)

n = np.array(
    [0, 1, 2]
)[:, np.newaxis]

steering_vectors = np.exp(
    +1j * np.pi * n * np.sin(theta_rad)
)
print(
    "Steering matrix shape:",
    steering_vectors.shape
)


# =====================================================
# REARRANGE DATA
# =====================================================

V_temp = np.transpose(
    V_clean,
    (1, 2, 0)
)

print(
    "Beamforming input shape:",
    V_temp.shape
)


# =====================================================
# COMPUTE BEAMFORMED POWER
# =====================================================

beamformed_signals = np.dot(
    V_temp,
    steering_vectors
)

beamformed_power = (
    np.abs(beamformed_signals) ** 2
)

print(
    "Beamformed map shape:",
    beamformed_power.shape
)

best_angles = []

for f in range(num_frames):

    frame_map = beamformed_power[f]

    idx = np.argmax(frame_map)

    bin_idx, angle_idx = np.unravel_index(
        idx,
        frame_map.shape
    )

    best_angles.append(theta_grid[angle_idx])

print("\nFirst 50 detected angles:")
print(best_angles[:50])
# =====================================================
# TRACK TARGET
# =====================================================

peak_ranges = []
peak_angles = []
peak_powers = []

for f in range(num_frames):

    frame_map = beamformed_power[f]

    idx = np.argmax(frame_map)

    bin_idx, angle_idx = np.unravel_index(
        idx,
        frame_map.shape
    )

    power_val = frame_map[
        bin_idx,
        angle_idx
    ]

    peak_ranges.append(bin_idx)
    peak_angles.append(theta_grid[angle_idx])
    peak_powers.append(power_val)

peak_ranges = np.array(peak_ranges)
peak_angles = np.array(peak_angles)
peak_powers = np.array(peak_powers)


# =====================================================
# FILTER WEAK DETECTIONS
# =====================================================

threshold = np.max(
    peak_powers
) * 0.05

valid_mask = (
    peak_powers > threshold

)

print(
    "Valid detections:",
    np.sum(valid_mask),
    "/",
    len(valid_mask)
)


track_bins = np.where(
    valid_mask,
    peak_ranges,
    np.nan
)

track_angles = np.where(
    valid_mask,
    peak_angles,
    np.nan
)

valid_angles = track_angles[~np.isnan(track_angles)]

print("Unique angles:")
print(np.unique(valid_angles)[:20])

print("Positive count:", np.sum(valid_angles > 0))
print("Negative count:", np.sum(valid_angles < 0))


# =====================================================
# PRINT SUMMARY
# =====================================================

print("\n========== RESULTS ==========")

print(
    "Mean Angle:",
    np.nanmean(track_angles)
)

print(
    "Min Angle:",
    np.nanmin(track_angles)
)

print(
    "Max Angle:",
    np.nanmax(track_angles)
)

print(
    "Mean Range Bin:",
    np.nanmean(track_bins)
)


# =====================================================
# PLOT
# =====================================================

fig, axs = plt.subplots(
    2,
    1,
    figsize=(12, 8),
    sharex=True
)

axs[0].plot(
    track_bins,
    lw=2,
    color="blue"
)

axs[0].set_title(
    "Target Range Tracking"
)

axs[0].set_ylabel(
    "Range Bin"
)

axs[0].grid(True)


axs[1].plot(
    track_angles,
    lw=2,
    color="orange"
)

axs[1].set_title(
    "Target Angle Tracking"
)

axs[1].set_ylabel(
    "Angle (deg)"
)

axs[1].set_xlabel(
    "Frame"
)

axs[1].grid(True)

plt.tight_layout()

plt.savefig(
    "target_tracking_aoa.png",
    dpi=300
)

print(
    "\nSaved target_tracking_aoa.png"
)

plt.show()