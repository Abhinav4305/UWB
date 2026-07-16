import argparse
import os
import numpy as np
import torch
from torch.utils.data import DataLoader
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

# Import the V2 dataset and model
from x7_train_4class_v2 import X7GestureDatasetV2, GestureCNN_X7_V2, N_CLASSES, GESTURE_NAMES, BATCH_SIZE

def run_eval(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Using device: {device}")
    
    # Load dataset (No augmentation during evaluation)
    print(f"[INFO] Loading dataset from '{args.data}'...")
    dataset = X7GestureDatasetV2(args.data, augment=False)
    
    if len(dataset) == 0:
        print("[ERROR] No data found.")
        return
        
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=False)
    
    # Initialize V2 8-channel model
    model = GestureCNN_X7_V2(n_classes=N_CLASSES).to(device)
    
    if not os.path.exists(args.model_path):
        print(f"[ERROR] Model weights not found at {args.model_path}")
        return
        
    print(f"[INFO] Loading model weights from '{args.model_path}'...")
    model.load_state_dict(torch.load(args.model_path, map_location=device))
    model.eval()
    
    all_preds = []
    all_labels = []
    
    print("[INFO] Evaluating model...")
    with torch.no_grad():
        for x, y in loader:
            outputs = model(x.to(device))
            preds = torch.argmax(outputs, dim=1)
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(y.cpu().numpy())
            
    # Calculate Metrics
    acc = accuracy_score(all_labels, all_preds)
    cm = confusion_matrix(all_labels, all_preds)
    
    print("\n" + "="*50)
    print(f" OVERALL V2 MODEL ACCURACY: {acc * 100:.2f}%")
    print("="*50)
    
    print("\n--- Confusion Matrix ---")
    header = f"{'True / Pred':<15} | " + " | ".join([f"{i:<3}" for i in range(N_CLASSES)])
    print(header)
    print("-" * len(header))
    for i, row in enumerate(cm):
        class_name = GESTURE_NAMES[i][:15] 
        row_str = " | ".join([f"{val:<3}" for val in row])
        print(f"{class_name:<15} | {row_str}")
        
    print("\n--- Classification Report ---")
    print(classification_report(all_labels, all_preds, target_names=GESTURE_NAMES))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="gesture_dataset_v2")
    parser.add_argument("--model_path", default="models/best_model_4class_v2.pth")
    args = parser.parse_args()
        
    run_eval(args)
