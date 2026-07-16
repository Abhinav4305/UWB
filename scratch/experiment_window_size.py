import os
import numpy as np
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import warnings
warnings.filterwarnings('ignore')

# Force non-interactive matplotlib
import matplotlib
matplotlib.use('Agg')

DATASET_PATH = r'c:\RR_02\dataset'
BATCH_SIZE = 8
EPOCHS = 20
LEARNING_RATE = 1e-3
N_CLASSES = 3

def load_new_radar_dataset(base_path, window_size=100):
    X_raw, y_labels, file_groups = [], [], []
    file_id = 0
    
    categories = {
        'no_movement': 0,
        'no_movement/0_people': 0,
        'no_movement/1_people': 1,
        'no_movement/2_people': 2,
        'movement/0_people': 0,
        'movement/1_people': 1,
        'movement/2_people': 2,
        'movement/0_peolple': 0,
        'movement/1_peolple': 1,
        'movement/2_peolple': 2,
    }
    
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
                radar_signal = np.mean(data_mag, axis=(1, 2))
                
                if radar_signal.shape[0] < window_size:
                    continue

                for i in range(0, radar_signal.shape[0] - window_size + 1, window_size):
                    X_raw.append(radar_signal[i : i + window_size, :])
                    y_labels.append(label)
                    file_groups.append(file_id)

                file_id += 1
            except Exception as e:
                pass

    return (np.array(X_raw, dtype=np.float32),
            np.array(y_labels, dtype=np.int32),
            np.array(file_groups, dtype=np.int32))

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
        layers.Dense(N_CLASSES, activation='softmax')
    ])
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LEARNING_RATE),
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    return model

window_sizes = [100, 200, 250, 500]
results = {}

for ws in window_sizes:
    print(f"\n==================================================")
    print(f" Testing WINDOW_SIZE = {ws}")
    print(f"==================================================")
    
    # Load dataset
    X, y, groups = load_new_radar_dataset(DATASET_PATH, ws)
    if len(X) == 0:
        print(f"No samples loaded for WINDOW_SIZE = {ws}")
        continue
        
    # File-level split
    unique_files = np.unique(groups)
    file_labels = np.array([y[groups == fid][0] for fid in unique_files])
    
    try:
        train_val_files, test_files = train_test_split(
            unique_files, test_size=0.2, random_state=42, stratify=file_labels
        )
        train_val_labels = np.array([y[groups == fid][0] for fid in train_val_files])
        train_files, val_files = train_test_split(
            train_val_files, test_size=0.19, random_state=42, stratify=train_val_labels
        )
    except Exception as e:
        print(f"Skipping WINDOW_SIZE = {ws} due to split error: {e}")
        continue
        
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
        
    # Calculate class weights
    class_weight = {}
    for cls in range(N_CLASSES):
        count = np.sum(y_train == cls)
        if count > 0:
            class_weight[cls] = len(y_train) / (N_CLASSES * count)
        else:
            class_weight[cls] = 1.0
            
    # Build & train
    model = build_1d_cnn(X_train.shape[1:])
    callbacks = [
        keras.callbacks.EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
    ]
    
    model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        class_weight=class_weight,
        callbacks=callbacks,
        verbose=0
    )
    
    # Evaluate
    y_pred_prob = model.predict(X_test, verbose=0)
    y_pred = np.argmax(y_pred_prob, axis=1)
    test_acc = accuracy_score(y_test, y_pred)
    
    print(f"Result for WINDOW_SIZE = {ws}: Test Accuracy = {test_acc * 100:.2f}% (Samples: {len(X)})")
    results[ws] = (test_acc * 100, len(X))
    
    # Clean up memory
    del model
    keras.backend.clear_session()

print("\n\n==================================================")
print(" EXPERIMENT SUMMARY")
print("==================================================")
for ws, (acc, count) in results.items():
    print(f"Window Size: {ws:4d} | Test Accuracy: {acc:6.2f}% | Total Windows: {count}")
print("==================================================")
