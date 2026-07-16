import numpy as np

def debug():
    data = np.load(r"C:\RR_02\gesture_dataset_v2\G01_SWIPE_LR\trial_1783401397.npy")
    frame_energy = np.sum(np.abs(data), axis=(1, 2, 3))
    peak_frame = np.argmax(frame_energy)
    
    print("Shape:", data.shape)
    print("Energies:", np.round(frame_energy[:10], 2))
    print("Peak:", peak_frame)
    
debug()
