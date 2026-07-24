import os
import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, confusion_matrix, ConfusionMatrixDisplay,
    classification_report
)

# --- CONFIGURATION ---
DATASET_PATH = r'c:\RR_02\human_detection'
WINDOW_SIZE = 50
BATCH_SIZE = 8
EPOCHS = 50
LEARNING_RATE = 1e-3

def load_new_radar_dataset(base_path, window_size=100):
    X_raw, y_labels, file_groups, file_names = [], [], [], []
    file_id = 0
    
    # Binary classification: 0 for no presence, 1 for presence
    categories = {
        'movement/0_people': 0,
        'movement/1_people': 1,
        'movement/2_people': 1,
        'movement/3_people': 1,
        'movement/4_people': 1,
        'movement/5_people': 1,
        '2_people': 1,
        '3_people': 1,
    }
    
    print(f"Scanning for .npy files in {base_path}...")
    
    for category, label in categories.items():
        cat_dir = os.path.join(base_path, category)
        if not os.path.exists(cat_dir):
            continue
            
        for file in os.listdir(cat_dir):
            if not file.endswith('.npy'):
                continue
                
            file_path = os.path.join(cat_dir, file)
            try:
                # Load raw complex64 data
                data = np.load(file_path)
                data_mag = np.abs(data)
                
                # Average across channels (TX0/1, RX0/1) for stability
                if data_mag.ndim == 4:
                    radar_signal = np.mean(data_mag, axis=(1, 2))
                elif data_mag.ndim == 2:
                    radar_signal = data_mag
                else:
                    radar_signal = data_mag
                
                # Standardize fast-time bins to 339
                if radar_signal.shape[1] < 339:
                    radar_signal = np.pad(radar_signal, ((0, 0), (0, 339 - radar_signal.shape[1])))
                elif radar_signal.shape[1] > 339:
                    radar_signal = radar_signal[:, :339]
                
                if radar_signal.shape[0] < window_size:
                    continue

                # Extract sliding windows
                windows_added = 0
                stride = 50
                for i in range(0, radar_signal.shape[0] - window_size + 1, stride):
                    X_raw.append(radar_signal[i : i + window_size, :])
                    y_labels.append(label)
                    file_groups.append(file_id)
                    windows_added += 1

                if windows_added > 0:
                    rel_path = os.path.join(category, file)
                    file_names.append(rel_path)
                    file_id += 1
            except Exception as e:
                print(f"Error loading {file}: {e}")

    return (np.array(X_raw, dtype=np.float32),
            np.array(y_labels, dtype=np.int32),
            np.array(file_groups, dtype=np.int32),
            file_names)

def build_1d_cnn(input_shape):
    model = keras.Sequential([
        layers.Conv1D(16, kernel_size=7, activation='relu', padding='same',
                      input_shape=input_shape),
        layers.BatchNormalization(),
        layers.MaxPooling1D(pool_size=4),
        layers.Conv1D(32, kernel_size=5, activation='relu', padding='same'),
        layers.BatchNormalization(),
        layers.MaxPooling1D(pool_size=4),
        layers.Conv1D(64, kernel_size=3, activation='relu', padding='same'),
        layers.BatchNormalization(),
        layers.MaxPooling1D(pool_size=4),
        layers.GlobalAveragePooling1D(),
        layers.Dropout(0.3),
        layers.Dense(32, activation='relu'),
        layers.Dropout(0.2),
        layers.Dense(1, activation='sigmoid') # Binary classification
    ])
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LEARNING_RATE),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    return model

def main():
    X, y, groups, fnames = load_new_radar_dataset(DATASET_PATH, WINDOW_SIZE)
    if len(X) == 0:
        print("No valid data loaded. Please check dataset path.")
        return
        
    n_files = len(np.unique(groups))
    print(f"\nLoaded {len(X)} windows from {n_files} files")
    print(f"Shape per window: {X[0].shape}")
    
    counts = dict(zip(*np.unique(y, return_counts=True)))
    print(f"Class distribution: {counts}")

    # File-Level Train/Test Split
    unique_files = np.unique(groups)
    file_labels = np.array([y[groups == fid][0] for fid in unique_files])

    # Stratified split requires at least 2 files per class. Handling simple split if too few files.
    try:
        train_val_files, test_files = train_test_split(
            unique_files, test_size=0.2, random_state=42, stratify=file_labels
        )
        train_val_labels = np.array([y[groups == fid][0] for fid in train_val_files])
        train_files, val_files = train_test_split(
            train_val_files, test_size=0.19, random_state=42, stratify=train_val_labels
        )
    except ValueError:
        print("Warning: Not enough files for stratified split, doing random split.")
        train_val_files, test_files = train_test_split(unique_files, test_size=0.2, random_state=42)
        train_files, val_files = train_test_split(train_val_files, test_size=0.19, random_state=42)
        

    train_mask = np.isin(groups, train_files)
    val_mask = np.isin(groups, val_files)
    test_mask = np.isin(groups, test_files)

    X_train, y_train = X[train_mask].copy(), y[train_mask]
    X_val, y_val = X[val_mask].copy(), y[val_mask]
    X_test, y_test = X[test_mask].copy(), y[test_mask]

    # Normalize per-sample
    for split_X in [X_train, X_val, X_test]:
        mean = np.mean(split_X, axis=(1, 2), keepdims=True)
        std = np.std(split_X, axis=(1, 2), keepdims=True) + 1e-8
        split_X[:] = (split_X - mean) / std

    print(f"\n--- FILE-LEVEL SPLIT ---")
    print(f"Train size: {X_train.shape[0]} windows")
    print(f"Val size:   {X_val.shape[0]} windows")
    print(f"Test size:  {X_test.shape[0]} windows")

    model = build_1d_cnn(X_train.shape[1:])
    model.summary()

    callbacks = [
        keras.callbacks.EarlyStopping(monitor='val_loss', patience=7, restore_best_weights=True),
        keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, min_lr=1e-6)
    ]

    # Class weights
    class_weight = {}
    for cls in [0, 1]:
        count = np.sum(y_train == cls)
        if count > 0:
            class_weight[cls] = len(y_train) / (2.0 * count)
        else:
            class_weight[cls] = 1.0

    print(f"Class weights: {class_weight}")

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        class_weight=class_weight,
        callbacks=callbacks,
        verbose=1
    )
    
    print("\n✅ Training complete!")

    # Evaluation
    print("\nEvaluating on test set...")
    loss, accuracy = model.evaluate(X_test, y_test)
    print(f"Test Accuracy: {accuracy*100:.2f}%")
    
    y_pred_prob = model.predict(X_test)
    y_pred = (y_pred_prob > 0.5).astype(int).flatten()
    
    print(f"\n{classification_report(y_test, y_pred)}")

    # Save model
    model.save('presence_detection_1d_cnn.h5')
    print("Model saved to presence_detection_1d_cnn.h5")

if __name__ == "__main__":
    main()
