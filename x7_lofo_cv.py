import argparse
import os
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Subset
from sklearn.model_selection import GroupKFold

# Import the dataset and model from the existing script
from x7_train_6class import X7GestureDataset, GestureCNN_X7, N_CLASSES, BATCH_SIZE

def run_lofo(args):
    # Load entire dataset
    print("[INFO] Loading full dataset for cross-validation...")
    full_dataset = X7GestureDataset(args.data, augment=False)
    
    if len(full_dataset) == 0:
        print("[ERROR] No data found.")
        return

    # Extract file_ids (groups) and labels for stratified/grouped splitting
    groups = [sample[2] for sample in full_dataset.samples]
    labels = [sample[1] for sample in full_dataset.samples]
    
    # Using GroupKFold to simulate Leave-One-File-Out across K folds to save time
    # True LOFO (K=144) would take ~2 hours for 50 epochs. K=5 takes ~4 minutes.
    k_folds = args.folds
    gkf = GroupKFold(n_splits=k_folds)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Using device: {device}")
    print(f"[INFO] Running {k_folds}-Fold Cross-Validation (Grouped by File ID)...")
    
    fold_accuracies = []
    
    for fold, (train_idx, val_idx) in enumerate(gkf.split(full_dataset, labels, groups)):
        print(f"\n--- Fold {fold + 1}/{k_folds} ---")
        
        # Create subsets
        train_sub = Subset(full_dataset, train_idx)
        val_sub = Subset(full_dataset, val_idx)
        
        # DataLoaders
        train_loader = DataLoader(train_sub, batch_size=BATCH_SIZE, shuffle=True, drop_last=False)
        val_loader = DataLoader(val_sub, batch_size=BATCH_SIZE, shuffle=False)
        
        # Initialize fresh model for this fold
        model = GestureCNN_X7(n_classes=N_CLASSES).to(device)
        crit = nn.CrossEntropyLoss()
        opt = optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
        
        best_val_acc = 0.0
        
        # Train for a set number of epochs
        for ep in range(1, args.epochs + 1):
            model.train()
            # Note: Augmentation could be dynamically applied here in a custom collate_fn 
            # or by modifying the dataset class, but for strict CV we keep it simple.
            for x, y in train_loader:
                opt.zero_grad()
                loss = crit(model(x.to(device)), y.to(device))
                loss.backward()
                opt.step()
                
            # Validate
            model.eval()
            correct, total = 0, 0
            with torch.no_grad():
                for x, y in val_loader:
                    preds = torch.argmax(model(x.to(device)), dim=1)
                    correct += (preds == y.to(device)).sum().item()
                    total += y.size(0)
            
            val_acc = correct / total if total > 0 else 0
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                
        print(f"Fold {fold + 1} Best Validation Accuracy: {best_val_acc * 100:.2f}%")
        fold_accuracies.append(best_val_acc)
        
    avg_acc = np.mean(fold_accuracies)
    print("\n" + "="*40)
    print(f"[RESULT] {k_folds}-Fold CV Average Accuracy: {avg_acc * 100:.2f}%")
    print("="*40)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="gesture_dataset")
    parser.add_argument("--epochs", type=int, default=30, help="Epochs per fold")
    parser.add_argument("--folds", type=int, default=5, help="Number of folds (approximates LOFO)")
    args = parser.parse_args()
    
    # We need sklearn for GroupKFold
    try:
        import sklearn
    except ImportError:
        print("[INFO] Installing scikit-learn for GroupKFold...")
        os.system("pip install scikit-learn")
        
    run_lofo(args)
