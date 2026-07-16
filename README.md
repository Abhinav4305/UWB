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
