import json
import os
import sys
import traceback

notebook_path = r'c:\RR_02\Human_sensing_1D_CNN.ipynb'

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Force non-interactive matplotlib backend
import matplotlib
matplotlib.use('Agg')

globals_dict = {}

print("Running all notebook cells sequentially to verify end-to-end execution...")

for idx, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        if not source.strip():
            continue
            
        # Skip sys.executable printing or cell containing sys.executable
        if 'sys.executable' in source:
            print(f"\n--- Skipping Cell {idx} (sys.executable check) ---")
            continue
            
        print(f"\n--- Executing Cell {idx} ---")
        print(f"Code snippet (first 100 chars): {source.strip()[:100]}...")
        
        try:
            # Execute code cell in shared globals dictionary
            exec(source, globals_dict)
            print(f"✅ Cell {idx} completed successfully.")
        except Exception as e:
            print(f"❌ Cell {idx} failed with error: {e}")
            traceback.print_exc()
            sys.exit(1)

print("\n🎉 All cells executed successfully!")
print("Checking for generated models:")
keras_path = '1d_cnn_human_detection.keras'
tflite_path = '1d_cnn_human_detection.tflite'
print(f"Keras model exists: {os.path.exists(keras_path)} (Size: {os.path.getsize(keras_path) if os.path.exists(keras_path) else 0} bytes)")
print(f"TFLite model exists: {os.path.exists(tflite_path)} (Size: {os.path.getsize(tflite_path) if os.path.exists(tflite_path) else 0} bytes)")
