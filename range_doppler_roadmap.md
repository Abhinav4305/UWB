# Future Roadmap: Range-Doppler Heatmap Processing

To push the model accuracy beyond 90%, the next evolution of this UWB radar project involves shifting from feeding **Raw I/Q Data** to feeding **Range-Doppler Heatmaps** into the CNN.

This document outlines the physics, the math, and a structured plan for implementing this upgrade in the future.

---

## 1. The Physics: Why Range-Doppler?

Currently, our AI learns directly from the raw **Complex I/Q (Phase) Data**. It looks at tiny sub-millimeter delays across the antennas over a time window to infer motion. While effective, it places a massive mathematical burden on the CNN to calculate velocity and direction from scratch using raw wave patterns.

**The Micro-Doppler Effect**
When you swipe your hand, different parts of your hand (fingertips, palm, wrist) move at slightly different velocities. 
- A hand moving *towards* the radar compresses the radar waves (Positive Doppler Shift).
- A hand moving *away* from the radar stretches the waves (Negative Doppler Shift).

A **Range-Doppler Map (RDM)** is a 2D Heatmap that plots **Distance (Range)** on the Y-axis and **Velocity (Doppler)** on the X-axis. 
Instead of the CNN struggling to decipher raw phase shifts, it is handed a beautiful, colorful image where a swipe clearly looks like a glowing blob moving across specific velocity and distance thresholds.

## 2. The Math: How it Works in Code

To generate these heatmaps, we use a fundamental mathematical algorithm called the **Fast Fourier Transform (FFT)**.

### Step-by-step Transformation
1. **Range FFT (Fast Time):** The radar hardware inherently performs the first FFT to separate the bouncing waves into "Range Bins" (determining *where* the object is). We already have this data.
2. **Doppler FFT (Slow Time):** We collect a sequence of frames (e.g., 64 frames). We then run a *second* FFT across the time dimension for every single range bin.
3. **The Result:** The Doppler FFT extracts the hidden velocity frequencies inside the raw phase data. The output is a 2D Matrix (Range vs. Velocity).

*Pseudo-code for the future pipeline:*
```python
# 1. Collect a time-window of raw radar frames (Shape: [64_frames, 34_range_bins])
raw_window = get_radar_frames()

# 2. Apply a Hanning Window (smooths the edges so the math works cleaner)
windowed_data = raw_window * np.hanning(64)[:, None]

# 3. Perform a 1D FFT across the time dimension (axis=0)
doppler_complex = np.fft.fftshift(np.fft.fft(windowed_data, axis=0), axes=0)

# 4. Convert complex numbers to absolute power (Heatmap Intensity)
range_doppler_heatmap = 20 * np.log10(np.abs(doppler_complex) + 1e-10)
```

## 3. The CNN Architecture Upgrade

Once the data is converted into Range-Doppler Heatmaps, the Neural Network architecture changes dramatically:

- **Current Model:** A 1D/2D CNN trying to extract temporal relationships across sequential radar frames.
- **Future Model:** A standard **Image Vision CNN** (like ResNet-18 or MobileNet). 

Because the FFT algorithm handles all the physics and time-domain math, the neural network no longer has to understand "time." It simply looks at the 2D Heatmap as a static picture. A Left-to-Right swipe creates a completely different visual "smudge" on the heatmap than a Right-to-Left swipe. 

## 4. Structured Implementation Plan (When Ready)

When you are ready to implement this in the future, the steps will be:

1. **Modify the Recording Script (`x7_record_1m.py`):**
   - Keep recording raw I/Q data exactly as we do now. Saving raw data ensures we can test different FFT algorithms later without having to re-record subjects.

2. **Create a Data Pre-processor:**
   - Build a script (`generate_heatmaps.py`) that loops through the `gesture_dataset_1m` folder.
   - Run the Doppler FFT algorithm on every `.npy` file.
   - Save the output as 2D NumPy arrays (the heatmaps) in a new folder called `gesture_heatmaps_1m`.

3. **Build the Vision Model (`x7_train_vision.py`):**
   - Throw away the current `GestureCNN_X7_V2` architecture.
   - Import a lightweight computer vision model (e.g., `torchvision.models.resnet18`).
   - Train the vision model directly on the heatmaps.

By offloading the hardest physics calculations to the FFT algorithm, the CNN will likely jump from 85% accuracy directly into the 93%+ range, making it incredibly resilient to random noise!
