# Core Working Principle — X7 UWB Radar Sensing Project

> One document explaining **how this whole project works**, end to end: the radar
> physics, the raw data, the signal-processing core that every script shares, and
> the two application arcs built on top of it (gesture / people sensing, and
> UWB↔camera collision prediction).

---

## 0. The one-sentence idea

A single **Novelda X7 impulse-radio ultra-wideband (IR-UWB) radar** emits tiny
radio pulses, listens to the echoes as **complex I/Q samples across range bins**,
and everything in this repo is a different way of turning that echo stream into
meaning — *what moved, how far away, how fast, in which direction, and how many
people/objects are there.*

Two things stay constant no matter which script you run:

1. **The sensor** — Novelda X7, ~7.3 GHz carrier, ~40 FPS, 2 TX × 2 RX antennas,
   raw `complex64` baseband over 96 or 192 range bins.
2. **The core preprocessing** — *magnitude / phase from I+jQ → remove the static
   background (MTI clutter subtraction) → normalize → feed a model or a peak
   detector.* Every application below is a variation on this pipeline.

---

## 1. The hardware & physics

### 1.1 Impulse-radio UWB
The X7 sends an extremely short radio pulse and samples the returning echo. The
round-trip delay maps to **distance**; the pulse is sampled into **range bins**
(each bin ≈ a slice of distance). This is why the raw data is indexed by *range
bin* — bin 0 is closest, higher bins are farther out.

| Parameter | Value | Notes |
|-----------|-------|-------|
| Carrier frequency | ~7.3 GHz | 5.8–8.3 GHz band |
| Bandwidth | ~500 MHz | gives fine range resolution |
| Frame rate | 40 FPS (10–40 configurable) | 25 ms per frame |
| Range | 0–~9.6 m (96 bins) or 0–~19.2 m (192 bins) | preset-dependent |
| Bin width | ≈ 0.1 m/bin (nominal) | **authoritative value = SDK-reported `bin_length`** |
| Antennas | 2 TX × 2 RX | forms a MIMO virtual array |

> ⚠️ **Never hardcode bin width.** The true meters-per-bin and range offset are
> reported by the SDK at runtime (`bin_length`, `range_offset`) and depend on the
> preset. `range_m = bin_index * bin_length + range_offset`.

### 1.2 Complex I/Q — why the data is `complex64`
The radar does not return a plain "reflection strength". It returns a **complex
number `I + jQ`** per range bin per antenna. From it you get:

- **Magnitude** `|I+jQ| = sqrt(I² + Q²)` → *how strong* the reflection is (object size / proximity).
- **Phase** `∠(I+jQ)` → *sub-millimeter position* of the target inside the radar wave. Phase is what encodes micro-motion (breathing) and direction of arrival.

### 1.3 MIMO → direction (Angle of Arrival)
A single antenna gives only distance. The X7 alternates its **2 TX and 2 RX**
antennas to synthesize **4 virtual antennas** (2×2). Because they sit a few mm
apart, an echo hits them at slightly different times → a measurable **phase shift
between antennas**. That phase difference *is* the Angle of Arrival:

- Hand swiping **left→right** → phase shift across the horizontal antenna pair.
- Hand swiping **up→down** → phase shift across the vertical pair.

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

- **Gesture / AoA arc (V2):** `(N_time, 2TX, 2RX, N_bins)` complex64 — *all 8 real+imag channels preserved.*
- **People-counting / collision arc:** averaged down to `(N_time, 2RX, N_bins)` or `(N_time, N_bins)` complex64.

Each recording is a `.npy` array plus a `_meta.json` capturing timestamp,
duration, scenario/label, and the SDK-reported `bin_length` / `range_offset`
(so range can always be reconstructed authoritatively).

### The V1 bug that shaped the design
An early recorder (V1) mangled the data down to 4 channels and **zeroed the phase**,
mixing left/right antennas together — the model was effectively blind to
direction. `x7_record_v2.py` fixed this by preserving all 8 channels (real+imag
of all 4 TX/RX pairs). This is the single most important data-quality lesson in
the repo (see `v1_vs_v2_comparison.md`).

---

## 3. The shared signal-processing core

Every application applies some subset of these five stages. This is *the* core
working principle.

```
raw complex I/Q  ──►  1. magnitude / channel split
                 ──►  2. channel averaging (SNR ↑)
                 ──►  3. MTI static-clutter subtraction   ◄── the crucial step
                 ──►  4a. range peak detection  (→ distance)
                 ──►  4b. CNN classification     (→ gesture / people count)
                 ──►  5. velocity estimation     (phase-Doppler OR range-rate)
```

### Stage 1 — Magnitude / phase extraction
`|frame|` gives reflected energy per bin. For direction work, the real & imag
parts are kept separately so phase survives.

### Stage 2 — Channel averaging (SNR)
Averaging across the 2 RX (and/or 2 TX) antennas cancels uncorrelated noise while
keeping the coherent target signal → ~3 dB SNR improvement.

### Stage 3 — MTI static-clutter subtraction (the key trick)
Stationary objects — seats, walls, dashboard, roof — produce **huge** reflections
(80–90 dB) that bury a breathing person (50–60 dB). We subtract the **time-mean**
of the signal so anything that didn't move disappears, leaving only moving
targets:

```python
clutter = np.mean(signal_over_time, axis=0, keepdims=True)  # background
clean   = signal_over_time - clutter                        # moving targets only
```

This "Moving Target Indicator" step is what makes both breathing-detection
(people counting) and gesture detection possible. In the gesture pipeline it's
done per-window on the stacked 8-channel tensor.

### Stage 4a — Range peak detection (collision arc)
`argmax` of the clutter-subtracted signal → the strongest reflection's bin →
distance via `bin * bin_length + range_offset`. Confidence = peak vs. noise floor.

### Stage 4b — CNN classification (gesture / people arc)
Instead of hand-crafted features, the cleaned tensor goes straight into a neural
net that learns the patterns (see §4).

### Stage 5 — Velocity: two complementary channels
- **Phase-Doppler (inter-frame):** differentiate phase between successive 40 Hz
  frames. **Hard Nyquist limit ≈ ±0.41 m/s** — only good for *micro-motion*
  (breathing, slow hand). Vehicle speeds alias completely and are meaningless.
- **Range-rate `v = -d(range)/dt`:** track the range peak over time and take its
  slope. **No Nyquist limit** — this is what the collision arc uses for real
  closing speeds. (Implemented as `RangeRateEstimator` in `uwb_signal_processor.py`.)

> Rule of thumb: **phase-Doppler for vitals/gestures, range-rate for collisions.**

---

## 4. Application arc A — Gesture & people sensing (repo root)

Built on the CNN branch of the core. Same radar, same MTI step, different heads.

### 4.1 People counting (0 / 1 / 2 people) — `Human_sensing_1D_CNN*.ipynb`
- Detects **how many people** (0, 1, 2) are inside a vehicle by sensing breathing
  micro-motion after clutter subtraction.
- **1D CNN** over sliding windows of the range signal.
- Key tuning found empirically (see `README.md`):
  - Stride = 50 (50% window overlap) balances augmentation vs. correlation.
  - **Clutter subtraction + stride 50 → 87% test accuracy** (+13.7% over baseline).
  - LOFO (Leave-One-File-Out) validation is noisier because classes 1 & 2 have
    very few source files.
- Exports: `1d_cnn_human_detection.keras` and a quantized `.tflite` for embedded
  deployment.

### 4.2 Directional gesture recognition — `x7_gesture*.py` / `x7_train*.py`
- Recognizes hand gestures: **SWIPE_LR, SWIPE_RL, SWIPE_UD, SWIPE_DU, PUSH_IN**
  (5-class; also 4-class and 6-class variants exist).
- Preprocessing (`to_8channel_tensor` in `x7_train_1m.py`):
  1. Split the `(64, 2, 2, bins)` window into **8 channels** = real & imag of all
     4 TX/RX pairs.
  2. **MTI** — subtract the per-window time-mean.
  3. **Per-window z-score** normalization (prevents mode collapse).
- **Peak-centered windowing:** find the max-energy frame and place it near the end
  of the 64-frame window, so the model learns to fire *the instant* a gesture peaks.
- **Augmentation** (train only): random time-shift of the peak, amplitude scaling
  (simulates hand distance), **random global phase rotation** (makes the model
  distance-invariant), and complex noise injection.
- **Model `GestureCNN_X7_V2`:** a 2D CNN (8-channel input → Conv/BN/ReLU/MaxPool
  stack → adaptive pool → FC classifier with dropout), trained with Adam, cosine
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

## 5. Application arc B — UWB↔Camera collision prediction (`RR_09/`)

A separate, self-contained sub-project that reuses the *same radar and the same
core pipeline* but aims at **automotive ADAS collision prediction** instead of
classification. It deliberately drops the gesture/people models.

### 5.1 Goal
Predict collisions by fusing:
- **UWB radar** → range + closing velocity, works in any lighting/weather.
- **Camera (future phase)** → object class + 2D localization + visual context.
- **Sensor fusion** → Kalman-filtered tracking → **Time-To-Collision (TTC)** →
  warning.

### 5.2 Three-phase plan
- **Phase 1 (current): UWB mastery** — `uwb_signal_processor.py` implements
  magnitude → channel avg → clutter sub → range peak → **range-rate velocity**.
  `validate_uwb.py` replays recordings offline (no hardware) and flags aliased
  phase-Doppler readings. Ground truth = a **tape measure** (a mono webcam has no
  depth), passed via `--distance`.
- **Phase 2: Camera integration** — intrinsics/extrinsics calibration, object
  detection (YOLO-class), temporal alignment of camera & UWB frames, project
  radar detections into the image.
- **Phase 3: Fusion** — Kalman filter over `[px, py, vx, vy, ax, ay]`, data
  association (match radar tracks ↔ camera detections), TTC + risk scoring.
  `TTC = solve(0.5·a_rel·t² + v_rel·t + d = 0)`; warn if `TTC < threshold`.

### 5.3 Portability (important design property)
`RR_09/` is **self-contained** — the X7 SDK (`PySignalFlow`), firmware, and DLLs
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
| Phase-Doppler caps at ±0.41 m/s | Nyquist at 40 FPS | use range-rate for fast targets |
| No elevation angle | 2×2 array is mostly horizontal | fuse camera for height |
| Clutter residual (~20 dB) after MTI | subtraction isn't perfect | thresholding, multi-frame integration |
| Poor accuracy < ~1 m | near-field non-linearity | camera backup for close range |
| Few source files per class | small dataset | overlap augmentation; LOFO variance expected |
| Weather/lighting (camera) | mono cam, no depth | UWB is the all-weather anchor |

---

## 7. Mental model / TL;DR

1. **One radar, complex echoes.** X7 gives `I+jQ` per range bin per antenna at 40 FPS.
2. **Magnitude = how strong, phase = where/how it moves, antenna phase-diff = direction.**
3. **Subtract the static background (MTI)** — this is what reveals breathing, hands, and moving obstacles.
4. **Then either:** feed a **CNN** (gestures, people counting) **or** run **peak-detection + range-rate** (collision distance & closing speed).
5. **Velocity has two regimes:** phase-Doppler for micro-motion (<0.41 m/s), range-rate for real-world speeds.
6. **`RR_09/` extends the same core** toward camera fusion + Kalman + TTC for ADAS, and is fully portable/self-contained.

### Where to read more
- `readme_angle_of_arrival.md` — direction / AoA physics.
- `v1_vs_v2_comparison.md` — the 8-channel data-quality lesson.
- `README.md` (root) — people-counting results & tuning.
- `RR_09/README.md`, `RR_09/UWB_SENSOR_ANALYSIS.md`, `RR_09/TECHNICAL_SPECIFICATION.md` — collision-prediction architecture & signal math.
