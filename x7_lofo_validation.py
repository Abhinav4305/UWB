import os
import torch
import numpy as np
from pathlib import Path
from torch.utils.data import DataLoader
from x7_train_4class_v2 import X7GestureDatasetV2, GestureCNN_X7_V2, N_CLASSES

def evaluate_lofo():
    print("[INFO] Starting Leave-One-Feature-Out (LOFO) Validation...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Load dataset
    dataset = X7GestureDatasetV2(root="gesture_dataset_v2", augment=False)
    loader = DataLoader(dataset, batch_size=32, shuffle=False)
    
    # Load model
    model = GestureCNN_X7_V2(n_classes=N_CLASSES).to(device)
    model.load_state_dict(torch.load("models/best_model_4class_v2.pth", map_location=device, weights_only=True))
    model.eval()

    # Calculate Baseline Accuracy
    def get_accuracy(zero_channel_idx=None):
        correct = 0
        total = 0
        with torch.no_grad():
            for x, y in loader:
                x = x.to(device)
                
                if zero_channel_idx is not None:
                    # Zero out the specific feature channel
                    x[:, zero_channel_idx, :, :] = 0.0
                    
                outputs = model(x)
                _, preds = torch.max(outputs, 1)
                total += y.size(0)
                correct += (preds == y.to(device)).sum().item()
        return (correct / total) * 100 if total > 0 else 0

    baseline_acc = get_accuracy()
    print(f"\nBaseline Model Accuracy (All Channels): {baseline_acc:.2f}%\n")
    
    channels = [
        "TX0_RX0 (Real)", "TX0_RX0 (Imag)", 
        "TX0_RX1 (Real)", "TX0_RX1 (Imag)",
        "TX1_RX0 (Real)", "TX1_RX0 (Imag)", 
        "TX1_RX1 (Real)", "TX1_RX1 (Imag)"
    ]
    
    print("--- LOFO Feature Importance ---")
    print("Feature                  | Accuracy | Drop")
    print("-" * 50)
    
    for i, feature_name in enumerate(channels):
        lofo_acc = get_accuracy(zero_channel_idx=i)
        drop = baseline_acc - lofo_acc
        print(f"{feature_name:<24} |  {lofo_acc:>5.2f}% | {-drop:>5.2f}%")
        
if __name__ == "__main__":
    evaluate_lofo()
