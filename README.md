# Walkthrough: Multi-Class In-Vehicle People Counting (0, 1, 2 People)

This walkthrough documents the implementation, testing, and optimization of the 3-class people counting model using raw IR-UWB radar data, replacing the previous binary classification pipeline.

## 1. Objectives & Requirements
* **Goal:** Detect the exact number of people present ($0$, $1$, or $2$) instead of binary presence vs. absence.
* **Dataset Constraints:** 
  * Class 0 (0 People): `no_movement` base files and `no_movement/0_people` subfolder.
  * Class 1 (1 Person): `no_movement/1_people` subfolder.
  * Class 2 (2 People): `no_movement/2_people` subfolder.
  * Avoid using files directly in the base `movement` folder.
* **Visualization Updates:** Update confusion matrix display names, true class prediction confidence histograms, and Leave-One-File-Out (LOFO) bar colors to reflect the 3 distinct classes.

---

## 2. Advanced Preprocessing: Static Clutter Subtraction
Static objects inside the vehicle (seats, roof panels, dashboard) create large reflections that hide the micro-movements of chest expansions (breathing). We implemented **moving target indicator (MTI) clutter subtraction** inside the data loader by subtracting the average reflection profile over the temporal axis of the raw signal:

```python
# Average across channels (TX0/1, RX0/1) for stability
radar_signal = np.mean(data_mag, axis=(1, 2))

# Subtract static clutter (background average subtraction) over range bins
radar_signal = radar_signal - np.mean(radar_signal, axis=0, keepdims=True)
```

By removing the static clutter before segmenting into sliding windows, we isolate target micro-movements cleanly.

---

## 3. Sliding Window Stride Optimization

We found that while high overlap (`stride = 20` or 80% overlap) significantly augments the training set (to 546 windows), it introduces highly correlated sequences. This caused the model to overfit overlap patterns.

To solve this, we optimized the sliding window parameter to **`stride = 50` (50% overlap)**. This provides a balance of:
* Augmented sample count (234 windows).
* Regularization to reduce correlation between adjacent time slices.

```python
                # Extract sliding windows with 50% overlap (stride = 50)
                windows_added = 0
                stride = 50
                for i in range(0, radar_signal.shape[0] - window_size + 1, stride):
                    X_raw.append(radar_signal[i : i + window_size, :])
                    y_labels.append(label)
                    file_groups.append(file_id)
                    windows_added += 1
```

---

## 4. End-to-End Validation & Training Run Results

We ran the notebook end-to-end using the local venv python interpreter. All cells executed successfully with the following outputs:

### A. Loaded Dataset Breakdown (Stride = 50 + Clutter Subtraction)
* **Class 0 (0 People):** 15 files (10 `no_movement` + 5 `0_people` baseline) $\rightarrow$ 135 windows.
* **Class 1 (1 Person):** 5 files (`1_people` baseline) $\rightarrow$ 45 windows.
* **Class 2 (2 People):** 6 files (`2_people` baseline) $\rightarrow$ 54 windows.
* **Total:** 234 windows from 26 unique files.

### B. Validation Results Comparison
Below is the progress comparison of the model's test accuracy across the various changes:

| Metric | Non-Overlapping (Stride=100) | Overlapping (Stride=20) | Overlapping (Stride=50) | Stride=50 + Clutter Subtraction |
| :--- | :---: | :---: | :---: | :---: |
| **Total Windows** | 130 | 546 | 234 | **234** |
| **Test Accuracy** | 73.33% | 62.70% | 75.93% | **87.04%** (**+11.11%** improvement) |
| **LOFO Accuracy** | 77.69% | 84.62% | 78.63% | **62.82%** |

* **Generalization Success:** Adding static clutter subtraction combined with the optimized `stride = 50` overlap boosted the holdout test accuracy to **87.04%** (+11.11% over the stride = 50 baseline, and +13.71% over the original stride = 100 baseline).
* **LOFO Variance:** Because the dataset has very few files for Class 1 (5 files) and Class 2 (6 files), holding out a file from these classes during LOFO leaves the training set under-represented (only 4 or 5 files) for that class, which explains the lower LOFO validation score.

### C. Deployment Exports
* Keras model `1d_cnn_human_detection.keras` (~323.9 KB) was exported.
* TFLite model `1d_cnn_human_detection.tflite` (~36.2 KB) was compiled and quantized successfully.

All updates to the visualization plots (confusion matrix, confidence histograms, and LOFO bar charts) are fully integrated into the notebook and will display correctly when run.


# Core Working Principle â€” X7 UWB Radar Sensing Project

> One document explaining **how this whole project works**, end to end: the radar
> physics, the raw data, the signal-processing core that every script shares, and
> the two application arcs built on top of it (gesture / people sensing, and
> UWBâ†”camera collision prediction).

---

## 0. The one-sentence idea

A single **Novelda X7 impulse-radio ultra-wideband (IR-UWB) radar** emits tiny
radio pulses, listens to the echoes as **complex I/Q samples across range bins**,
and everything in this repo is a different way of turning that echo stream into
meaning â€” *what moved, how far away, how fast, in which direction, and how many
people/objects are there.*

Two things stay constant no matter which script you run:

1. **The sensor** â€” Novelda X7, ~7.3 GHz carrier, ~40 FPS, 2 TX Ã— 2 RX antennas,
   raw `complex64` baseband over 96 or 192 range bins.
2. **The core preprocessing** â€” *magnitude / phase from I+jQ â†’ remove the static
   background (MTI clutter subtraction) â†’ normalize â†’ feed a model or a peak
   detector.* Every application below is a variation on this pipeline.

---

## 1. The hardware & physics

### 1.1 Impulse-radio UWB
The X7 sends an extremely short radio pulse and samples the returning echo. The
round-trip delay maps to **distance**; the pulse is sampled into **range bins**
(each bin â‰ˆ a slice of distance). This is why the raw data is indexed by *range
bin* â€” bin 0 is closest, higher bins are farther out.

| Parameter | Value | Notes |
|-----------|-------|-------|
| Carrier frequency | ~7.3 GHz | 5.8â€“8.3 GHz band |
| Bandwidth | ~500 MHz | gives fine range resolution |
| Frame rate | 40 FPS (10â€“40 configurable) | 25 ms per frame |
| Range | 0â€“~9.6 m (96 bins) or 0â€“~19.2 m (192 bins) | preset-dependent |
| Bin width | â‰ˆ 0.1 m/bin (nominal) | **authoritative value = SDK-reported `bin_length`** |
| Antennas | 2 TX Ã— 2 RX | forms a MIMO virtual array |

> âš ï¸ **Never hardcode bin width.** The true meters-per-bin and range offset are
> reported by the SDK at runtime (`bin_length`, `range_offset`) and depend on the
> preset. `range_m = bin_index * bin_length + range_offset`.

### 1.2 Complex I/Q â€” why the data is `complex64`
The radar does not return a plain "reflection strength". It returns a **complex
number `I + jQ`** per range bin per antenna. From it you get:

- **Magnitude** `|I+jQ| = sqrt(IÂ² + QÂ²)` â†’ *how strong* the reflection is (object size / proximity).
- **Phase** `âˆ (I+jQ)` â†’ *sub-millimeter position* of the target inside the radar wave. Phase is what encodes micro-motion (breathing) and direction of arrival.

### 1.3 MIMO â†’ direction (Angle of Arrival)
A single antenna gives only distance. The X7 alternates its **2 TX and 2 RX**
antennas to synthesize **4 virtual antennas** (2Ã—2). Because they sit a few mm
apart, an echo hits them at slightly different times â†’ a measurable **phase shift
between antennas**. That phase difference *is* the Angle of Arrival:

- Hand swiping **leftâ†’right** â†’ phase shift across the horizontal antenna pair.
- Hand swiping **upâ†’down** â†’ phase shift across the vertical pair.

Classical radar extracts angle with trig algorithms (MUSIC/ESPRIT). **This
project skips that math** and feeds the raw 4-channel complex matrix to a CNN,
which learns the phase-shift patterns itself. (See `readme_angle_of_arrival.md`.)

---

## 2. The raw data format

The SDK's frame callback fires at ~40 Hz:

```python
def _frame_callback(trx_mask, data, seq_num, timestamp, range_offset, bin_length):
    # data: complex64, shape (num_frames, 2TX, 2RX, N_bins)
```

Depending on the recorder, data is stored as either:

- **Gesture / AoA arc (V2):** `(N_time, 2TX, 2RX, N_bins)` complex64 â€” *all 8 real+imag channels preserved.*
- **People-counting / collision arc:** averaged down to `(N_time, 2RX, N_bins)` or `(N_time, N_bins)` complex64.

Each recording is a `.npy` array plus a `_meta.json` capturing timestamp,
duration, scenario/label, and the SDK-reported `bin_length` / `range_offset`
(so range can always be reconstructed authoritatively).

### The V1 bug that shaped the design
An early recorder (V1) mangled the data down to 4 channels and **zeroed the phase**,
mixing left/right antennas together â€” the model was effectively blind to
direction. `x7_record_v2.py` fixed this by preserving all 8 channels (real+imag
of all 4 TX/RX pairs). This is the single most important data-quality lesson in
the repo (see `v1_vs_v2_comparison.md`).

---

## 3. The shared signal-processing core

Every application applies some subset of these five stages. This is *the* core
working principle.

```
raw complex I/Q  â”€â”€â–º  1. magnitude / channel split
                 â”€â”€â–º  2. channel averaging (SNR â†‘)
                 â”€â”€â–º  3. MTI static-clutter subtraction   â—„â”€â”€ the crucial step
                 â”€â”€â–º  4a. range peak detection  (â†’ distance)
                 â”€â”€â–º  4b. CNN classification     (â†’ gesture / people count)
                 â”€â”€â–º  5. velocity estimation     (phase-Doppler OR range-rate)
```

### Stage 1 â€” Magnitude / phase extraction
`|frame|` gives reflected energy per bin. For direction work, the real & imag
parts are kept separately so phase survives.

### Stage 2 â€” Channel averaging (SNR)
Averaging across the 2 RX (and/or 2 TX) antennas cancels uncorrelated noise while
keeping the coherent target signal â†’ ~3 dB SNR improvement.

### Stage 3 â€” MTI static-clutter subtraction (the key trick)
Stationary objects â€” seats, walls, dashboard, roof â€” produce **huge** reflections
(80â€“90 dB) that bury a breathing person (50â€“60 dB). We subtract the **time-mean**
of the signal so anything that didn't move disappears, leaving only moving
targets:

```python
clutter = np.mean(signal_over_time, axis=0, keepdims=True)  # background
clean   = signal_over_time - clutter                        # moving targets only
```

This "Moving Target Indicator" step is what makes both breathing-detection
(people counting) and gesture detection possible. In the gesture pipeline it's
done per-window on the stacked 8-channel tensor.

### Stage 4a â€” Range peak detection (collision arc)
`argmax` of the clutter-subtracted signal â†’ the strongest reflection's bin â†’
distance via `bin * bin_length + range_offset`. Confidence = peak vs. noise floor.

### Stage 4b â€” CNN classification (gesture / people arc)
Instead of hand-crafted features, the cleaned tensor goes straight into a neural
net that learns the patterns (see Â§4).

### Stage 5 â€” Velocity: two complementary channels
- **Phase-Doppler (inter-frame):** differentiate phase between successive 40 Hz
  frames. **Hard Nyquist limit â‰ˆ Â±0.41 m/s** â€” only good for *micro-motion*
  (breathing, slow hand). Vehicle speeds alias completely and are meaningless.
- **Range-rate `v = -d(range)/dt`:** track the range peak over time and take its
  slope. **No Nyquist limit** â€” this is what the collision arc uses for real
  closing speeds. (Implemented as `RangeRateEstimator` in `uwb_signal_processor.py`.)

> Rule of thumb: **phase-Doppler for vitals/gestures, range-rate for collisions.**

---

## 4. Application arc A â€” Gesture & people sensing (repo root)

Built on the CNN branch of the core. Same radar, same MTI step, different heads.

### 4.1 People counting (0 / 1 / 2 people) â€” `Human_sensing_1D_CNN*.ipynb`
- Detects **how many people** (0, 1, 2) are inside a vehicle by sensing breathing
  micro-motion after clutter subtraction.
- **1D CNN** over sliding windows of the range signal.
- Key tuning found empirically (see `README.md`):
  - Stride = 50 (50% window overlap) balances augmentation vs. correlation.
  - **Clutter subtraction + stride 50 â†’ 87% test accuracy** (+13.7% over baseline).
  - LOFO (Leave-One-File-Out) validation is noisier because classes 1 & 2 have
    very few source files.
- Exports: `1d_cnn_human_detection.keras` and a quantized `.tflite` for embedded
  deployment.

### 4.2 Directional gesture recognition â€” `x7_gesture*.py` / `x7_train*.py`
- Recognizes hand gestures: **SWIPE_LR, SWIPE_RL, SWIPE_UD, SWIPE_DU, PUSH_IN**
  (5-class; also 4-class and 6-class variants exist).
- Preprocessing (`to_8channel_tensor` in `x7_train_1m.py`):
  1. Split the `(64, 2, 2, bins)` window into **8 channels** = real & imag of all
     4 TX/RX pairs.
  2. **MTI** â€” subtract the per-window time-mean.
  3. **Per-window z-score** normalization (prevents mode collapse).
- **Peak-centered windowing:** find the max-energy frame and place it near the end
  of the 64-frame window, so the model learns to fire *the instant* a gesture peaks.
- **Augmentation** (train only): random time-shift of the peak, amplitude scaling
  (simulates hand distance), **random global phase rotation** (makes the model
  distance-invariant), and complex noise injection.
- **Model `GestureCNN_X7_V2`:** a 2D CNN (8-channel input â†’ Conv/BN/ReLU/MaxPool
  stack â†’ adaptive pool â†’ FC classifier with dropout), trained with Adam, cosine
  LR schedule, and label smoothing.

### 4.3 Supporting scripts (root)
| Script | Role |
|--------|------|
| `x7_record*.py` | capture labeled radar recordings (`_v2`, `_1m`, `_presence`, `_4class` variants) |
| `x7_train*.py` | train the gesture CNN (class-count variants) |
| `x7_eval*.py`, `eval_human.py` | evaluate trained models |
| `x7_lofo_cv.py`, `x7_lofo_validation.py` | Leave-One-File-Out cross-validation |
| `x7_occupancy.py` | occupancy sensing |
| `live_count.py`, `live_replay.py`, `rdm.py` | live/replay visualization |
| `default_preset.json` | radar acquisition preset |

---

## 5. Application arc B â€” UWBâ†”Camera collision prediction (`RR_09/`)

A separate, self-contained sub-project that reuses the *same radar and the same
core pipeline* but aims at **automotive ADAS collision prediction** instead of
classification. It deliberately drops the gesture/people models.

### 5.1 Goal
Predict collisions by fusing:
- **UWB radar** â†’ range + closing velocity, works in any lighting/weather.
- **Camera (future phase)** â†’ object class + 2D localization + visual context.
- **Sensor fusion** â†’ Kalman-filtered tracking â†’ **Time-To-Collision (TTC)** â†’
  warning.

### 5.2 Three-phase plan
- **Phase 1 (current): UWB mastery** â€” `uwb_signal_processor.py` implements
  magnitude â†’ channel avg â†’ clutter sub â†’ range peak â†’ **range-rate velocity**.
  `validate_uwb.py` replays recordings offline (no hardware) and flags aliased
  phase-Doppler readings. Ground truth = a **tape measure** (a mono webcam has no
  depth), passed via `--distance`.
- **Phase 2: Camera integration** â€” intrinsics/extrinsics calibration, object
  detection (YOLO-class), temporal alignment of camera & UWB frames, project
  radar detections into the image.
- **Phase 3: Fusion** â€” Kalman filter over `[px, py, vx, vy, ax, ay]`, data
  association (match radar tracks â†” camera detections), TTC + risk scoring.
  `TTC = solve(0.5Â·a_relÂ·tÂ² + v_relÂ·t + d = 0)`; warn if `TTC < threshold`.

### 5.3 Portability (important design property)
`RR_09/` is **self-contained** â€” the X7 SDK (`PySignalFlow`), firmware, and DLLs
(`X7_SDK_0.6_x64-win/`, `bin/`, `lib/`, `LibFT4222*`) are bundled, and
`x7_env.py` resolves every path relative to the repo root. It does **not** depend
on `C:\RR_02`. Requires Python **3.10** (must match `PySignalFlow.cp310`).
Offline analysis needs no hardware; live capture needs the X7 plugged in + the
**FT4222 USB driver**.

### 5.4 Key RR_09 scripts
| Script | Role |
|--------|------|
| `uwb_signal_processor.py` | core: `UWBSignalProcessor`, `RangeRateEstimator`, `CollisionPredictor` |
| `validate_uwb.py` | offline pipeline validator on recordings |
| `x7_record.py` / `record_synced.py` | UWB-only / UWB+webcam synchronized recorder |
| `x7_env.py` | portable SDK & firmware path bootstrap |
| `calibrate_camera.py`, `collect_camera.py`, `analyze_camera.py` | camera side |
| `fusion.py`, `fusion_ui.py` | fusion logic + visualization |
| `uwb_pointcloud.py`, `uwb_polar.py`, `uwb_occupancy.py`, `uwb_analytics.py` | UWB analysis/visualization |

---

## 6. Known limitations (both arcs)

| Limitation | Why | Mitigation |
|-----------|-----|-----------|
| Phase-Doppler caps at Â±0.41 m/s | Nyquist at 40 FPS | use range-rate for fast targets |
| No elevation angle | 2Ã—2 array is mostly horizontal | fuse camera for height |
| Clutter residual (~20 dB) after MTI | subtraction isn't perfect | thresholding, multi-frame integration |
| Poor accuracy < ~1 m | near-field non-linearity | camera backup for close range |
| Few source files per class | small dataset | overlap augmentation; LOFO variance expected |
| Weather/lighting (camera) | mono cam, no depth | UWB is the all-weather anchor |

---

## 7. Mental model / TL;DR

1. **One radar, complex echoes.** X7 gives `I+jQ` per range bin per antenna at 40 FPS.
2. **Magnitude = how strong, phase = where/how it moves, antenna phase-diff = direction.**
3. **Subtract the static background (MTI)** â€” this is what reveals breathing, hands, and moving obstacles.
4. **Then either:** feed a **CNN** (gestures, people counting) **or** run **peak-detection + range-rate** (collision distance & closing speed).
5. **Velocity has two regimes:** phase-Doppler for micro-motion (<0.41 m/s), range-rate for real-world speeds.
6. **`RR_09/` extends the same core** toward camera fusion + Kalman + TTC for ADAS, and is fully portable/self-contained.

### Where to read more
- `readme_angle_of_arrival.md` â€” direction / AoA physics.
- `v1_vs_v2_comparison.md` â€” the 8-channel data-quality lesson.
- `README.md` (root) â€” people-counting results & tuning.
- `RR_09/README.md`, `RR_09/UWB_SENSOR_ANALYSIS.md`, `RR_09/TECHNICAL_SPECIFICATION.md` â€” collision-prediction architecture & signal math.


# Angle of Arrival & Directional Gesture Detection

This document explains the physical and mathematical mechanisms that allow the X7 UWB (Ultra-Wideband) radar to determine the exact direction of a hand gesture (e.g., Left-to-Right vs. Right-to-Left, or Up-to-Down).

## 1. The Hardware: 2x2 MIMO Antennas
A single radar antenna can only tell you the *distance* of an object, not its direction. To figure out whether a hand is moving left, right, up, or down, the X7 radar utilizes a **MIMO (Multiple-Input Multiple-Output)** antenna array.

Specifically, it uses:
- **2 Transmit (TX) Antennas**
- **2 Receive (RX) Antennas**

By rapidly alternating which antenna is transmitting and receiving, the radar creates **4 "Virtual" Antennas** (`2 TX Ã— 2 RX`). Because these antennas are physically separated by a few millimeters on the silicon chip, they each "see" the room from a slightly different angle.

## 2. The Data: Complex I/Q Signals
The radar does not just give us a standard real number for the reflection strength. It gives us **Complex I/Q (In-phase and Quadrature)** data.
Mathematically, this is represented as a complex number: `I + jQ`.

From this complex number, we can calculate two things:
1. **Amplitude (Magnitude):** How strong the reflection is (tells us how large the hand is).
2. **Phase (Angle):** The exact sub-millimeter position of the hand within the radar wave.

## 3. The Physics: Phase Interferometry
When you swipe your hand from **Left to Right**:
1. The radar wave bounces off your hand and travels back to the sensor.
2. Because your hand is on the left side of the chip, the reflected wave hits the **Left RX Antenna** a fraction of a picosecond *before* it hits the **Right RX Antenna**.
3. This microscopic time delay causes a **Phase Shift** between the I/Q signals recorded by the left and right antennas. 

Conversely, if you swipe from **Up to Down**, the phase shift occurs across the vertical axis of the virtual antennas. By measuring the phase differences between all 4 virtual antennas, the system can calculate the exact 3D Angle of Arrival (AoA) of the hand.

## 4. The Brain: Convolutional Neural Networks (CNN)
In traditional radar engineering, calculating the Angle of Arrival requires complex trigonometry algorithms (like MUSIC or ESPRIT). 

However, in our pipeline, we skip the manual math entirely. During data collection, we extract a 4-dimensional matrix of shape:
`[Time (Frames), TX Antennas, RX Antennas, Range Bins]`
*(e.g., `[64, 2, 2, 34]`)*

We feed these raw complex matrices directly into a **Convolutional Neural Network (CNN)**. Over the course of training, the CNN's filters automatically learn to recognize the specific Phase Shift patterns that correspond to a Left-to-Right swipe versus a Right-to-Left swipe, resulting in highly robust directional gesture detection!

