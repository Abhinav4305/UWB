import numpy as np
import torch
import glob
from x7_gesture_4class_v2 import GestureCNN_X7_V2, N_CLASSES, GESTURE_NAMES, preprocess_x7native_v2

def simulate_live():
    device = torch.device("cpu")
    model = GestureCNN_X7_V2(n_classes=N_CLASSES).to(device)
    model.load_state_dict(torch.load("models/best_model_4class_v2.pth", map_location=device, weights_only=True))
    model.eval()

    files = glob.glob(r"C:\RR_02\gesture_dataset_v2\G01_SWIPE_LR\*.npy")[:5]
    for f in files:
        raw = np.load(f)
        
        # Simulate live buffer logic
        complex_buffer = raw.copy() # (100, 2, 2, 96)
        
        # Gesture has finished. Find peak energy!
        frame_energy = np.sum(np.abs(complex_buffer), axis=(1, 2, 3))
        peak_frame = np.argmax(frame_energy)
        
        start = peak_frame - (64 // 2)
        if start < 0: start = 0
        if start + 64 > len(complex_buffer): start = len(complex_buffer) - 64
        
        centered_window = complex_buffer[start : start + 64]
        
        tensor, _ = preprocess_x7native_v2(centered_window)
        probs = torch.softmax(model(tensor), dim=1).detach().cpu().numpy()[0]
        
        pred_raw = GESTURE_NAMES[int(np.argmax(probs))]
        print(f"File {f.split('\\')[-1]}: Peak at {peak_frame}, Predicted: {pred_raw} ({np.max(probs)*100:.1f}%)")

if __name__ == "__main__":
    simulate_live()
