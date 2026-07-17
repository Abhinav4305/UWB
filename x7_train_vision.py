"""
train_gesture_x7_v2.py
====================
Trains a gesture recognition CNN on proper V2 X7-native data.
Expects data of shape (N, 2, 2, 96) complex64 (Time, TX, RX, Bins)
"""

import argparse
import os
from collections import defaultdict
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.models as models
from torch.utils.data import DataLoader, Dataset

# ── CONFIG ────────────────────────────────────────────────────────────────────
BATCH_SIZE = 16
WINDOW_SIZE = 64
GESTURE_FOLDERS = [
    "G01_SWIPE_LR", "G02_SWIPE_RL", "G03_SWIPE_UD", "G04_SWIPE_DU", "G05_PUSH_IN"
]
GESTURE_NAMES = ["SWIPE_LR", "SWIPE_RL", "SWIPE_UD", "SWIPE_DU", "PUSH_IN"]
N_CLASSES = 5

# ── PREPROCESSING ─────────────────────────────────────────────────────────────
def to_range_doppler_tensor(frames: np.ndarray) -> torch.Tensor:
    # frames shape: (64, 2, 2, 34) complex64
    w = frames
    if w.shape[3] > 34: w = w[:, :, :, :34]
    
    # 1. MTI Filter (Remove DC static clutter)
    w = w - np.mean(w, axis=0, keepdims=True)
    
    # 2. Hanning Window (Time Domain)
    w_hanning = w * np.hanning(w.shape[0])[:, None, None, None]
    
    # 3. FFT (Doppler)
    doppler_complex = np.fft.fftshift(np.fft.fft(w_hanning, axis=0), axes=0)
    
    # 4. Extract Power (dB) and Phase
    power = 20 * np.log10(np.abs(doppler_complex) + 1e-10)
    phase = np.angle(doppler_complex)
    
    # 5. Z-Score Normalization
    power = (power - np.mean(power)) / (np.std(power) + 1e-9)
    phase = phase / np.pi  # Normalize to [-1, 1]
    
    p_00, p_01 = power[:, 0, 0, :], power[:, 0, 1, :]
    p_10, p_11 = power[:, 1, 0, :], power[:, 1, 1, :]
    
    ph_00, ph_01 = phase[:, 0, 0, :], phase[:, 0, 1, :]
    ph_10, ph_11 = phase[:, 1, 0, :], phase[:, 1, 1, :]
    
    stacked = np.stack([p_00, p_01, p_10, p_11, ph_00, ph_01, ph_10, ph_11], axis=0)
    # PyTorch expects (Channels, H, W)
    return torch.tensor(stacked, dtype=torch.float32)

# ── DATASET ───────────────────────────────────────────────────────────────────
class X7GestureDatasetV2(Dataset):
    def __init__(self, root: str, augment: bool = False, file_ids: list = None):
        self.augment = augment
        self.samples = []
        root_path = Path(root)
        file_id = 0

        for label_idx, folder in enumerate(GESTURE_FOLDERS):
            class_dir = root_path / folder
            if not class_dir.exists(): continue
            npy_files = sorted(class_dir.rglob("*.npy"))
            for fp in npy_files:
                if file_ids is not None and file_id not in file_ids:
                    file_id += 1; continue
                try:
                    raw = np.load(fp)
                    # Skip files that are not V2 format
                    if raw.ndim != 4:
                        print(f"[WARN] Skipping {fp} - not a V2 recording. Wrong shape {raw.shape}")
                        continue
                    if raw.shape[0] < WINDOW_SIZE: continue
                    
                    # Store the full raw recording to allow dynamic shifting in __getitem__
                    self.samples.append((raw, label_idx, "gesture"))
                except Exception as e: print(f"[WARN] Error {fp}: {e}")
                file_id += 1
        print(f"[INFO] Loaded {len(self.samples)} raw recordings.")

    def __len__(self): return len(self.samples)
    def __getitem__(self, idx):
        raw, label, sample_type = self.samples[idx]
        
        # Find peak energy
        frame_energy = np.sum(np.abs(raw), axis=(1, 2, 3))
        peak_frame = int(np.argmax(frame_energy))
        
        # True gesture: Peak should be near the end of the window (Index 55)
        # This teaches the model to recognize the gesture instantly as it happens!
        start = peak_frame - 55
        if self.augment:
            # Train the network to recognize the peak anywhere from index 40 to 64
            start += np.random.randint(-15, 6)
            
        # Guarantee valid slice logic even if the gesture peak was at the extreme edges
        start = max(-WINDOW_SIZE + 1, min(len(raw) - 1, start))
            
        # Extract 64 frames. Pad with edge frames if out of bounds.
        window = np.zeros((WINDOW_SIZE, 2, 2, raw.shape[3]), dtype=np.complex64)
        
        raw_start = max(0, start)
        raw_end = min(len(raw), start + WINDOW_SIZE)
        
        win_start = max(0, -start)
        win_end = win_start + (raw_end - raw_start)
        
        window[win_start:win_end] = raw[raw_start:raw_end]
        
        # Pad missing parts to simulate standing still before/after the gesture
        if win_start > 0:
            window[:win_start] = raw[0]
        if win_end < WINDOW_SIZE:
            window[win_end:] = raw[-1]
            
        if self.augment:
            # Random scale to simulate different hand distances
            scale = np.random.uniform(0.6, 1.4)
            window = window * scale
            
            # Phase rotation: completely blind the model to micro-distances
            phase_shift = np.exp(1j * np.random.uniform(0, 2 * np.pi))
            window = window * phase_shift
            
            noise = (np.random.randn(*window.shape) + 1j * np.random.randn(*window.shape)) * 0.05
            window = window + noise.astype(np.complex64)
            
        return to_range_doppler_tensor(window), label

# ── MODEL ─────────────────────────────────────────────────────────────────────
class RangeDopplerResNet(nn.Module):
    def __init__(self, n_classes: int = N_CLASSES):
        super().__init__()
        self.resnet = models.resnet18(pretrained=False)
        # Modify the first layer to accept 8 channels instead of 3
        self.resnet.conv1 = nn.Conv2d(8, 64, kernel_size=7, stride=2, padding=3, bias=False)
        # Modify the fully connected layer for our 5 classes
        self.resnet.fc = nn.Linear(self.resnet.fc.in_features, n_classes)
        
    def forward(self, x):
        return self.resnet(x)

# ── MAIN ──────────────────────────────────────────────────────────────────────
def run(args):
    full_ds = X7GestureDatasetV2(args.data)
    if len(full_ds) == 0: return print("[ERROR] No data found.")

    from torch.utils.data import DataLoader, random_split
    
    dataset = X7GestureDatasetV2(args.data, augment=True)
    val_size = int(0.2 * len(dataset))
    train_size = len(dataset) - val_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    val_dataset.dataset.augment = False
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, drop_last=False)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
    
    device = torch.device("cpu")
    model = RangeDopplerResNet(n_classes=N_CLASSES).to(device)
    print("[DEBUG] Model initialized on CPU")
    crit = torch.nn.CrossEntropyLoss(label_smoothing=0.1)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    
    try:
        best_acc = 0.0
        os.makedirs(args.out, exist_ok=True)
        print("[DEBUG] Starting training loop")
        for ep in range(1, args.epochs + 1):
            model.train()
            total_loss = 0
            for x, y in train_loader:
                opt.zero_grad()
                loss = crit(model(x.to(device)), y.to(device))
                loss.backward()
                opt.step()
                total_loss += loss.item()
            
            # Validation
            model.eval()
            correct = 0
            with torch.no_grad():
                for x, y in val_loader:
                    preds = model(x.to(device)).argmax(dim=1)
                    correct += (preds == y.to(device)).sum().item()
            
            val_acc = correct / len(val_dataset)
            print(f"Epoch {ep:02d} - Loss: {total_loss/len(train_loader):.4f} - Val Acc: {val_acc*100:.1f}%")
            if val_acc > best_acc:
                best_acc = val_acc
                torch.save(model.state_dict(), os.path.join(args.out, "best_model_vision.pth"))
                
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("\n[INFO] Training interrupted.")
    print("[INFO] Training Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="gesture_dataset_1m")
    parser.add_argument("--out", default="models")
    parser.add_argument("--epochs", type=int, default=150)
    args = parser.parse_args()
    run(args)
