# live_rtm.py
# Improved live Range-Time Map for presence + gesture detection

import numpy as np
import matplotlib.pyplot as plt


plt.ion()

# -----------------------------
# Settings
# -----------------------------

RTM_LENGTH = 200

# Focus on likely human region
MIN_BIN = 5
MAX_BIN = 30

NUM_BINS = 96


buffer = np.zeros((RTM_LENGTH, NUM_BINS))


fig, ax = plt.subplots(figsize=(12, 6))

img = ax.imshow(
    np.zeros((MAX_BIN - MIN_BIN, RTM_LENGTH)),
    aspect="auto",
    origin="lower",
    cmap="jet"
)
plt.colorbar(img)

ax.set_title("Live Radar Range-Time Map")
ax.set_xlabel("Time")
ax.set_ylabel("Range Bin")


def update_rtm(frame):

    global buffer

    # Update rolling buffer
    buffer[:-1] = buffer[1:]
    buffer[-1] = frame

    # Wait until some frames arrive
    valid_rows = np.any(buffer != 0, axis=1)

    if np.sum(valid_rows) < 20:
        return

    # Absolute signal strength
    background = np.mean(buffer[-30:], axis=0)

    processed = np.abs(buffer - background)

    # Crop range bins
    cropped = processed[:, MIN_BIN:MAX_BIN]
    processed = processed / (np.std(processed) + 1e-6)

    # Update existing image
    img.set_data(cropped.T)

    # Auto-scale colors
    vmin = 0
    vmax = np.percentile(cropped,99)

    img.set_clim(vmin, vmax)

    ax.set_title(
        f"Live RTM | Bins {MIN_BIN}-{MAX_BIN}"
    )

    fig.canvas.draw_idle()
    fig.canvas.flush_events()
    plt.pause(0.001)
