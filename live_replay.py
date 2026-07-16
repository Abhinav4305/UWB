import os
import sys
import argparse
import time
from collections import deque
import numpy as np

# Suppress TensorFlow logging to keep terminal output clean
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import tensorflow as tf
from tensorflow import keras

def parse_args():
    parser = argparse.ArgumentParser(description="Offline Radar Recording Replay Validation")
    parser.add_argument(
        "--model", 
        type=str, 
        default="1d_cnn_human_detection.keras",
        help="Path to the Keras model file (.keras)"
    )
    parser.add_argument(
        "--recording", 
        type=str, 
        default="recording.npy",
        help="Path to the recording file (.npy)"
    )
    parser.add_argument(
        "--fps", 
        type=float, 
        default=60.0,
        help="Replay speed in frames per second (set to 0 for maximum speed)"
    )
    parser.add_argument(
        "--window-size", 
        type=int, 
        default=100,
        help="Sliding window size (number of frames)"
    )
    parser.add_argument(
        "--stride", 
        type=int, 
        default=10,
        help="Stride for runing inference (update frequency in frames)"
    )
    return parser.parse_args()

def locate_file(filename, fallback_paths):
    """
    Check if a file exists locally. If not, check fallback paths.
    """
    if os.path.exists(filename):
        return os.path.abspath(filename)
    
    for path in fallback_paths:
        full_path = os.path.join(path, filename) if not os.path.isabs(path) else path
        if os.path.exists(full_path):
            return os.path.abspath(full_path)
            
    # Also do a recursive search if not found
    for root, _, files in os.walk('.'):
        if filename in files:
            return os.path.abspath(os.path.join(root, filename))
            
    return None

def main():
    args = parse_args()
    
    # Define fallback directories to look for models and recordings
    fallback_model_paths = [
        "c:/RR_02",
        "c:/RR_02/scratch"
    ]
    fallback_recording_paths = [
        "c:/RR_02",
        "c:/RR_02/novelda-uwb-demos/Demos/RadarDirect/X7RadarDirectCallback/backup_old"
    ]
    
    # Locate model file
    model_path = locate_file(args.model, fallback_model_paths)
    if not model_path:
        print(f"Error: Model file '{args.model}' not found in current directory or fallbacks.")
        sys.exit(1)
        
    # Locate recording file
    recording_path = locate_file(args.recording, fallback_recording_paths)
    if not recording_path:
        # Check if the path given is already absolute and valid
        if os.path.exists(args.recording):
            recording_path = os.path.abspath(args.recording)
        else:
            print(f"Error: Recording file '{args.recording}' not found.")
            sys.exit(1)

    print(f"[*] Loading Keras model from: {model_path}")
    try:
        model = keras.models.load_model(model_path)
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)
        
    print(f"[*] Loading recording from: {recording_path}")
    try:
        recording = np.load(recording_path)
    except Exception as e:
        print(f"Error loading recording: {e}")
        sys.exit(1)
        
    print(f"[*] Recording shape: {recording.shape} | Dtype: {recording.dtype}")
    
    # Check dimensions
    # Expecting recording to be (N, 2, 2, 96) or similar
    if len(recording.shape) != 4 or recording.shape[1:4] != (2, 2, 96):
        print(f"Warning: Recording shape is {recording.shape}, expected (N, 2, 2, 96).")
        
    classes = ['0 People', '1 Person', '2 People']
    buffer = deque(maxlen=args.window_size)
    
    delay = 1.0 / args.fps if args.fps > 0 else 0.0
    print(f"[*] Starting playback at {args.fps if args.fps > 0 else 'maximum'} FPS...")
    print("-" * 40)
    
    frame_count = 0
    try:
        for frame in recording:
            frame_count += 1
            
            # 1. Apply absolute magnitude
            frame_mag = np.abs(frame)
            
            # 2. Average across TX/RX channels (axes 0 and 1)
            # Resulting shape: (96,)
            feature = np.mean(frame_mag, axis=(0, 1))
            
            # 3. Maintain buffer
            buffer.append(feature)
            
            # 4. Check if buffer is full and update interval matches
            if len(buffer) == args.window_size:
                steps_after_fill = frame_count - args.window_size
                if steps_after_fill % args.stride == 0:
                    # Create window of shape (100, 96)
                    window = np.array(buffer, dtype=np.float32)
                    
                    # Normalize exactly as during training:
                    window_mean = window.mean()
                    window_std = window.std()
                    window_normalized = (window - window_mean) / (window_std + 1e-8)
                    
                    # Reshape for Keras input: [1, 100, 96]
                    input_data = np.expand_dims(window_normalized, axis=0)
                    
                    # Run inference
                    predictions = model.predict(input_data, verbose=0)[0]
                    pred_class = int(np.argmax(predictions))
                    confidence = float(predictions[pred_class])
                    
                    # Map to class label
                    pred_label = classes[pred_class] if pred_class < len(classes) else f"Class {pred_class}"
                    
                    # Print frame summary
                    print(f"Frame: {frame_count}")
                    print(f"Prediction: {pred_label}")
                    print(f"Confidence: {confidence * 100:.0f}%")
                    print("-" * 30)
            
            # Control playback speed
            if delay > 0:
                time.sleep(delay)
                
    except KeyboardInterrupt:
        print("\n[*] Playback paused by user.")
    
    print(f"\n[*] Replay completed. Processed {frame_count} frames.")

if __name__ == "__main__":
    main()
