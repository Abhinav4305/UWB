import os
import numpy as np
import tensorflow as tf
from tensorflow import keras
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

def load_new_radar_dataset(base_path, window_size=100):
    X_raw, y_labels = [], []
    
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
                    window = radar_signal[i : i + window_size, :]
                    
                    # Global z-score normalisation just like live_count.py
                    window = (window - np.mean(window)) / (np.std(window) + 1e-8)
                    
                    X_raw.append(window)
                    y_labels.append(label)

            except Exception as e:
                pass

    return np.array(X_raw, dtype=np.float32), np.array(y_labels, dtype=np.int32)


def main():
    print("[*] Loading dataset...")
    X, y = load_new_radar_dataset(r'c:\RR_02\dataset', window_size=100)
    
    print(f"Loaded {len(X)} samples.")
    if len(X) == 0:
        print("No data found!")
        return

    print("[*] Loading model...")
    model = keras.models.load_model(r'c:\RR_02\1d_cnn_human_detection.keras')
    
    print("[*] Evaluating...")
    # Add dummy channel dimension if expected by the model? 
    # The model expects (None, 100, 96). Our X is (N, 100, 96).
    preds_prob = model.predict(X, verbose=0)
    preds = np.argmax(preds_prob, axis=1)
    
    acc = accuracy_score(y, preds)
    print("\n" + "="*50)
    print(f" OVERALL MODEL ACCURACY: {acc * 100:.2f}%")
    print("="*50)
    
    print("\n--- Confusion Matrix ---")
    cm = confusion_matrix(y, preds)
    print("True \\ Pred | 0 People | 1 Person | 2 People")
    for i, row in enumerate(cm):
        print(f"{i} People    | {row[0]:<8} | {row[1]:<8} | {row[2]:<8}")

    print("\n--- Classification Report ---")
    print(classification_report(y, preds, target_names=["0 People", "1 Person", "2 People"]))

if __name__ == "__main__":
    main()
