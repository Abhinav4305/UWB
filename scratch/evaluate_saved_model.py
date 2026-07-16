import os
import numpy as np
import tensorflow as tf
from tensorflow import keras
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# Configuration
DATASET_PATH = r'c:\RR_02\dataset'
WINDOW_SIZE = 100

def load_new_radar_dataset(base_path, window_size=100):
    X_raw, y_labels, file_groups, file_names = [], [], [], []
    file_id = 0
    categories = {'no_movement': 0, 'movement': 1}
    
    for category, label in categories.items():
        cat_dir = os.path.join(base_path, category)
        if not os.path.exists(cat_dir):
            continue
        for file in os.listdir(cat_dir):
            if not file.endswith('.npy'):
                continue
            file_path = os.path.join(cat_dir, file)
            try:
                data = np.load(file_path)
                data_mag = np.abs(data)
                # Average across channels (TX, RX)
                radar_signal = np.mean(data_mag, axis=(1, 2))
                if radar_signal.shape[0] < window_size:
                    continue
                windows_added = 0
                for i in range(0, radar_signal.shape[0] - window_size + 1, window_size):
                    X_raw.append(radar_signal[i : i + window_size, :])
                    y_labels.append(label)
                    file_groups.append(file_id)
                    windows_added += 1
                if windows_added > 0:
                    file_names.append(os.path.join(category, file))
                    file_id += 1
            except Exception as e:
                pass
    return (np.array(X_raw, dtype=np.float32),
            np.array(y_labels, dtype=np.int32),
            np.array(file_groups, dtype=np.int32),
            file_names)

print("Loading dataset...")
X, y, groups, fnames = load_new_radar_dataset(DATASET_PATH, WINDOW_SIZE)
if len(X) == 0:
    print("No data found!")
    exit(1)

# Perform split identically
unique_files = np.unique(groups)
file_labels = np.array([y[groups == fid][0] for fid in unique_files])
train_val_files, test_files = train_test_split(
    unique_files, test_size=0.2, random_state=42, stratify=file_labels
)
train_val_labels = np.array([y[groups == fid][0] for fid in train_val_files])
train_files, val_files = train_test_split(
    train_val_files, test_size=0.19, random_state=42, stratify=train_val_labels
)

train_mask = np.isin(groups, train_files)
val_mask = np.isin(groups, val_files)
test_mask = np.isin(groups, test_files)

X_train, y_train = X[train_mask].copy(), y[train_mask]
X_val, y_val = X[val_mask].copy(), y[val_mask]
X_test, y_test = X[test_mask].copy(), y[test_mask]

# Normalize
for split_X in [X_train, X_val, X_test]:
    mean = np.mean(split_X, axis=(1, 2), keepdims=True)
    std = np.std(split_X, axis=(1, 2), keepdims=True) + 1e-8
    split_X[:] = (split_X - mean) / std

model_path = r'c:\RR_02\1d_cnn_human_detection.keras'
if not os.path.exists(model_path):
    print("Model not found at", model_path)
    exit(1)

print("Loading saved Keras model...")
model = keras.models.load_model(model_path)

print("\nEvaluating model...")
train_loss, train_acc = model.evaluate(X_train, y_train, verbose=0)
val_loss, val_acc = model.evaluate(X_val, y_val, verbose=0)
test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)

print(f"Train Accuracy: {train_acc * 100:.2f}%")
print(f"Val Accuracy:   {val_acc * 100:.2f}%")
print(f"Test Accuracy:  {test_acc * 100:.2f}%")

y_pred_prob = model.predict(X_test, verbose=0).flatten()
y_pred = (y_pred_prob >= 0.5).astype(int)
print("\nClassification Report (Test Set):")
print(classification_report(y_test, y_pred, target_names=['Empty (0)', 'Occupied (1)']))
