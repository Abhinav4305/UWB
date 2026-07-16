import json
import os

notebook_path = r'c:\RR_02\Human_sensing_1D_CNN.ipynb'

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

print("Altering notebook cells to support 3-class people counting (0, 1, 2 people)...")

# Define replacement codes
config_source = [
    "# --- CONFIGURATION ---\n",
    "DATASET_PATH = r'c:\\RR_02\\dataset'\n",
    "WINDOW_SIZE = 100\n",
    "BATCH_SIZE = 8\n",
    "EPOCHS = 50\n",
    "LEARNING_RATE = 1e-3\n",
    "N_CLASSES = 3\n",
    "print(\"Environment Ready.\")"
]

loader_source = [
    "def load_new_radar_dataset(base_path, window_size=100):\n",
    "    \"\"\"\n",
    "    Loads recorded complex64 .npy files, converts them to magnitude, \n",
    "    and segments them into windowed frames for the 1D-CNN.\n",
    "    \"\"\"\n",
    "    X_raw, y_labels, file_groups, file_names = [], [], [], []\n",
    "    file_id = 0\n",
    "    \n",
    "    # Map folder names to class labels (0, 1, 2 people)\n",
    "    categories = {\n",
    "        'no_movement': 0,\n",
    "        '0_people': 0,\n",
    "        '1_people': 1,\n",
    "        '2_people': 2\n",
    "    }\n",
    "    \n",
    "    print(f\"Scanning for .npy files in {base_path}...\")\n",
    "    \n",
    "    for category, label in categories.items():\n",
    "        cat_dir = os.path.join(base_path, category)\n",
    "        if not os.path.exists(cat_dir):\n",
    "            continue\n",
    "            \n",
    "        for file in os.listdir(cat_dir):\n",
    "            if not file.endswith('.npy'):\n",
    "                continue\n",
    "                \n",
    "            file_path = os.path.join(cat_dir, file)\n",
    "            try:\n",
    "                # Load raw complex64 data: shape (num_frames, 2, 2, 96)\n",
    "                data = np.load(file_path)\n",
    "                data_mag = np.abs(data)\n",
    "                \n",
    "                # Average across channels (TX0/1, RX0/1) for stability\n",
    "                # Shape becomes: (num_frames, 96)\n",
    "                radar_signal = np.mean(data_mag, axis=(1, 2))\n",
    "                \n",
    "                if radar_signal.shape[0] < window_size:\n",
    "                    continue\n",
    "\n",
    "                # Extract sliding windows\n",
    "                windows_added = 0\n",
    "                for i in range(0, radar_signal.shape[0] - window_size + 1, window_size):\n",
    "                    X_raw.append(radar_signal[i : i + window_size, :])\n",
    "                    y_labels.append(label)\n",
    "                    file_groups.append(file_id)\n",
    "                    windows_added += 1\n",
    "\n",
    "                if windows_added > 0:\n",
    "                    rel_path = os.path.join(category, file)\n",
    "                    file_names.append(rel_path)\n",
    "                    file_id += 1\n",
    "            except Exception as e:\n",
    "                print(f\"Error loading {file}: {e}\")\n",
    "\n",
    "    return (np.array(X_raw, dtype=np.float32),\n",
    "            np.array(y_labels, dtype=np.int32),\n",
    "            np.array(file_groups, dtype=np.int32),\n",
    "            file_names)\n",
    "\n",
    "# Load the new dataset\n",
    "X, y, groups, fnames = load_new_radar_dataset(DATASET_PATH, WINDOW_SIZE)\n",
    "n_files = len(np.unique(groups))\n",
    "print(f\"\\nLoaded {len(X)} windows from {n_files} files\")\n",
    "print(f\"Shape per window: {X[0].shape}\")\n",
    "print(f\"Class distribution: {dict(zip(*np.unique(y, return_counts=True)))}\")\n",
    "\n",
    "# Show loaded details\n",
    "print(f\"\\n{'File':>4} | {'Windows':>7} | {'Class':>5} | Path\")\n",
    "print('-' * 70)\n",
    "for fid in np.unique(groups):\n",
    "    mask = groups == fid\n",
    "    lbl = y[mask][0]\n",
    "    print(f\"{fid:>4} | {np.sum(mask):>7} | {lbl:>5} | {fnames[fid]}\")"
]

model_source = [
    "def build_1d_cnn(input_shape):\n",
    "    model = keras.Sequential([\n",
    "        layers.Conv1D(16, kernel_size=7, activation='relu', padding='same',\n",
    "                      input_shape=input_shape),\n",
    "        layers.BatchNormalization(),\n",
    "        layers.MaxPooling1D(pool_size=4),\n",
    "        layers.Conv1D(32, kernel_size=5, activation='relu', padding='same'),\n",
    "        layers.BatchNormalization(),\n",
    "        layers.MaxPooling1D(pool_size=4),\n",
    "        layers.Conv1D(64, kernel_size=3, activation='relu', padding='same'),\n",
    "        layers.BatchNormalization(),\n",
    "        layers.MaxPooling1D(pool_size=4),\n",
    "        layers.GlobalAveragePooling1D(),\n",
    "        layers.Dropout(0.3),\n",
    "        layers.Dense(32, activation='relu'),\n",
    "        layers.Dropout(0.2),\n",
    "        layers.Dense(N_CLASSES, activation='softmax')\n",
    "    ])\n",
    "    model.compile(\n",
    "        optimizer=keras.optimizers.Adam(learning_rate=LEARNING_RATE),\n",
    "        loss='sparse_categorical_crossentropy',\n",
    "        metrics=['accuracy']\n",
    "    )\n",
    "    return model\n",
    "\n",
    "model = build_1d_cnn(X_train.shape[1:])\n",
    "model.summary()\n",
    "print(f\"\\nModel size: {model.count_params() * 4 / 1024:.1f} KB\")"
]

eval_source = [
    "y_pred_prob = model.predict(X_test)\n",
    "y_pred = np.argmax(y_pred_prob, axis=1)\n",
    "test_acc = accuracy_score(y_test, y_pred)\n",
    "\n",
    "print(f\"Test Accuracy: {test_acc * 100:.2f}%\")\n",
    "print(f\"\\n{classification_report(y_test, y_pred, target_names=['0 People', '1 Person', '2 People'])}\")"
]

sanity_source = [
    "print(\"=\" * 60)\n",
    "print(\"  SANITY CHECK 1: Prediction Confidence Distribution\")\n",
    "print(\"=\" * 60)\n",
    "print(\"If all predictions are near 1.0, the model is very\")\n",
    "print(\"confident. If clustered near 0.33, it's guessing.\\n\")\n",
    "\n",
    "fig, axes = plt.subplots(1, 2, figsize=(12, 4))\n",
    "\n",
    "# All predictions max confidence\n",
    "pred_conf = np.max(y_pred_prob, axis=1)\n",
    "axes[0].hist(pred_conf, bins=20, edgecolor='black', alpha=0.7, color='steelblue')\n",
    "axes[0].set_title('All Test Predictions Confidence', fontweight='bold')\n",
    "axes[0].set_xlabel('Max Predicted Probability')\n",
    "axes[0].set_ylabel('Count')\n",
    "\n",
    "# Per-class confidence\n",
    "for cls, color, name in [(0, '#55A868', '0 People'), (1, '#C44E52', '1 Person'), (2, '#4C72B0', '2 People')]:\n",
    "    mask = y_test == cls\n",
    "    if np.any(mask):\n",
    "        axes[1].hist(np.max(y_pred_prob[mask], axis=1), bins=20, alpha=0.6, color=color, label=name, edgecolor='black')\n",
    "axes[1].set_title('Confidence by True Class', fontweight='bold')\n",
    "axes[1].set_xlabel('Max Predicted Probability')\n",
    "axes[1].legend()\n",
    "plt.tight_layout()\n",
    "plt.show()\n",
    "\n",
    "for cls, name in [(0, '0 People'), (1, '1 Person'), (2, '2 People')]:\n",
    "    mask = y_test == cls\n",
    "    if np.any(mask):\n",
    "        print(f\"{name} samples  → mean confidence: {np.max(y_pred_prob[mask], axis=1).mean():.4f}\")"
]

# Walk cells and update
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = cell['source']
        source_str = "".join(source)
        
        # Match Config cell
        if '# --- CONFIGURATION ---' in source_str:
            print("Updating CONFIGURATION cell...")
            cell['source'] = config_source
            cell['outputs'] = []
            cell['execution_count'] = None
            
        # Match Data Loader cell
        elif 'load_radar_dataset' in source_str or 'load_new_radar_dataset' in source_str:
            print("Updating Data Loader cell...")
            cell['source'] = loader_source
            cell['outputs'] = []
            cell['execution_count'] = None
            
        # Match Model cell
        elif 'def build_1d_cnn' in source_str:
            print("Updating Model Builder cell...")
            cell['source'] = model_source
            cell['outputs'] = []
            cell['execution_count'] = None
            
        # Match Evaluation cell
        elif 'classification_report(y_test, y_pred' in source_str:
            print("Updating Evaluation cell...")
            cell['source'] = eval_source
            cell['outputs'] = []
            cell['execution_count'] = None
            
        # Match Sanity Check 1 cell
        elif 'SANITY CHECK 1: Prediction Confidence Distribution' in source_str:
            print("Updating Sanity Check 1 cell...")
            cell['source'] = sanity_source
            cell['outputs'] = []
            cell['execution_count'] = None

# Save updated notebook
with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Altered notebook successfully! Re-run notebook cells now.")
