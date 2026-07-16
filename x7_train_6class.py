"""
train_gesture_x7.py
====================
Trains a gesture recognition CNN on X7-native data.
Fixed to recursively find files as shown in edited-image.png.
"""

import argparse
import os
from collections import defaultdict
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset

# ── CONFIG ────────────────────────────────────────────────────────────────────
RANGE_BINS   = 96    # Fixed to match your data shape (..., 96)
WINDOW_SIZE  = 64    # Fits within your 72-frame recordings
STRIDE       = 40    
BATCH_SIZE   = 16
LEARNING_RATE = 3e-4
WEIGHT_DECAY  = 1e-4

GESTURE_FOLDERS = [
    'G01_SWIPE_LR', 'G02_SWIPE_RL', 'G03_SWIPE_UD', 'G04_SWIPE_DU',
    'G11_INWARD_PUSH', 'G12_EMPTY'
]
N_CLASSES = len(GESTURE_FOLDERS)

# ── PREPROCESSING ─────────────────────────────────────────────────────────────
def to_4channel_tensor(frames: np.ndarray) -> torch.Tensor:
    # frames shape: (64, 2, 96) complex64
    rx1 = frames[:, 0, :]
    rx2 = frames[:, 1, :]
    # Stack into (4, 64, 96)
    stacked = np.stack([np.real(rx1), np.imag(rx1), np.real(rx2), np.imag(rx2)], axis=0)
    
    # Global Z-score normalization for raw I/Q voltages
    mean = np.mean(stacked)
    std = np.std(stacked) + 1e-9
    norm = (stacked - mean) / std
    
    # PyTorch expects (Channels, H, W) -> (4, 96, 64)
    norm = np.transpose(norm, (0, 2, 1))
    return torch.from_numpy(norm).float()

# ── DATASET ───────────────────────────────────────────────────────────────────
class X7GestureDataset(Dataset):
    def __init__(self, root: str, augment: bool = False, file_ids: list = None):
        self.augment = augment
        self.samples = []
        root_path = Path(root)
        file_id = 0

        for label_idx, folder in enumerate(GESTURE_FOLDERS):
            class_dir = root_path / folder
            if not class_dir.exists(): continue
            # FIXED: Used rglob to find all files in subfolders shown in edited-image.png
            npy_files = sorted(class_dir.rglob("*.npy"))
            for fp in npy_files:
                if file_ids is not None and file_id not in file_ids:
                    file_id += 1; continue
                try:
                    raw = np.load(fp)
                    if raw.shape[0] < WINDOW_SIZE: continue
                    for start in range(0, raw.shape[0] - WINDOW_SIZE + 1, STRIDE):
                        self.samples.append((raw[start: start + WINDOW_SIZE], label_idx, file_id))
                except Exception as e: print(f"[WARN] Error {fp}: {e}")
                file_id += 1
        print(f"[INFO] Loaded {len(self.samples)} windows.")

    def __len__(self): return len(self.samples)
    def __getitem__(self, idx):
        window, label, _ = self.samples[idx]
        if self.augment:
            shift = np.random.randint(-15, 16)
            if shift > 0:
                window = np.concatenate([window[shift:], np.zeros((shift, 2, RANGE_BINS), np.complex64)])
            elif shift < 0:
                window = np.concatenate([np.zeros((-shift, 2, RANGE_BINS), np.complex64), window[:shift]])
            
            # Inject small complex noise
            noise = (np.random.randn(*window.shape) + 1j * np.random.randn(*window.shape)) * 0.05
            window = window + noise.astype(np.complex64)
            
        return to_4channel_tensor(window), label

# ── MODEL ─────────────────────────────────────────────────────────────────────
class GestureCNN_X7(nn.Module):
    def __init__(self, n_classes: int = N_CLASSES):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(4, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(128, 256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(True),
            nn.AdaptiveAvgPool2d((4, 4)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(), nn.Linear(256 * 16, 512), nn.ReLU(True), nn.Dropout(0.4),
            nn.Linear(512, 128), nn.ReLU(True), nn.Dropout(0.3), nn.Linear(128, n_classes),
        )
    def forward(self, x): return self.classifier(self.features(x))

# ── MAIN ──────────────────────────────────────────────────────────────────────
def run(args):
    full_ds = X7GestureDataset(args.data)
    if len(full_ds) == 0: return print("[ERROR] No data found.")

    from torch.utils.data import DataLoader, random_split
    
    dataset = X7GestureDataset(args.data, augment=True)
    val_size = int(0.2 * len(dataset))
    train_size = len(dataset) - val_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    # Disable augmentation on validation set
    val_dataset.dataset.augment = False
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, drop_last=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = GestureCNN_X7(n_classes=N_CLASSES).to(device)
    crit = nn.CrossEntropyLoss()
    opt = optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    
    try:
        best_acc = 0.0
        os.makedirs(args.out, exist_ok=True)
        for ep in range(1, args.epochs + 1):
            # Training
            model.train()
            train_dataset.dataset.augment = True
            total_loss = 0
            for x, y in train_loader:
                opt.zero_grad()
                loss = crit(model(x.to(device)), y.to(device))
                loss.backward(); opt.step()
                total_loss += loss.item()
                
            # Validation
            model.eval()
            train_dataset.dataset.augment = False # Disable for val
            correct, total = 0, 0
            with torch.no_grad():
                for x, y in val_loader:
                    preds = torch.argmax(model(x.to(device)), dim=1)
                    correct += (preds == y.to(device)).sum().item()
                    total += y.size(0)
            
            val_acc = correct / total if total > 0 else 0
            print(f"Epoch {ep:02d} - Loss: {total_loss/len(train_loader):.4f} - Val Acc: {val_acc*100:.1f}%")
            if val_acc > best_acc:
                best_acc = val_acc
                torch.save(model.state_dict(), os.path.join(args.out, "best_model_6class.pth"))
                
    except KeyboardInterrupt:
        print("\n[INFO] Training interrupted.")
    print("[INFO] Training Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="gesture_dataset")
    parser.add_argument("--out", default="models")
    parser.add_argument("--epochs", type=int, default=50)
    args = parser.parse_args()
    run(args)