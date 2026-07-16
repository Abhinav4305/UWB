import json
import os

notebook_path = r'c:\RR_02\Human_sensing_1D_CNN.ipynb'

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

print("Altering notebook cells to support 3-class people counting (0, 1, 2 people)...")

# Define replacement codes
config_source = [
    "import os\n",
    "import numpy as np\n",
    "import matplotlib.pyplot as plt\n",
    "import warnings\n",
    "warnings.filterwarnings('ignore')\n",
    "\n",
    "import tensorflow as tf\n",
    "from tensorflow import keras\n",
    "from tensorflow.keras import layers\n",
    "from sklearn.model_selection import train_test_split\n",
    "from sklearn.metrics import (\n",
    "    accuracy_score, confusion_matrix, ConfusionMatrixDisplay,\n",
    "    classification_report\n",
    ")\n",
    "\n",
    "# --- Verify Metal GPU ---\n",
    "gpus = tf.config.list_physical_devices('GPU')\n",
    "print(f\"TensorFlow version: {tf.__version__}\")\n",
    "if gpus:\n",
    "    print(f\"✅ Metal GPU detected: {gpus}\")\n",
    "    for gpu in gpus:\n",
    "        tf.config.experimental.set_memory_growth(gpu, True)\n",
    "else:\n",
    "    print(\"⚠️  No GPU found. Running on CPU.\")\n",
    "\n",
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
    "    # Exclude base movement files by not listing 'movement' as a category\n",
    "    categories = {\n",
    "        'no_movement': 0,\n",
    "        'no_movement/0_people': 0,\n",
    "        'no_movement/1_people': 1,\n",
    "        'no_movement/2_people': 2,\n",
    "        'movement/0_people': 0,\n",
    "        'movement/1_people': 1,\n",
    "        'movement/2_people': 2,\n",
    "        'movement/0_peolple': 0,\n",
    "        'movement/1_peolple': 1,\n",
    "        'movement/2_peolple': 2,\n",
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

train_source = [
    "callbacks = [\n",
    "    keras.callbacks.EarlyStopping(monitor='val_loss', patience=7, restore_best_weights=True),\n",
    "    keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, min_lr=1e-6)\n",
    "]\n",
    "\n",
    "# Calculate class weights for multiclass setup\n",
    "class_weight = {}\n",
    "for cls in range(N_CLASSES):\n",
    "    count = np.sum(y_train == cls)\n",
    "    if count > 0:\n",
    "        class_weight[cls] = len(y_train) / (N_CLASSES * count)\n",
    "    else:\n",
    "        class_weight[cls] = 1.0\n",
    "print(f\"Class weights: {class_weight}\")\n",
    "\n",
    "history = model.fit(\n",
    "    X_train, y_train,\n",
    "    validation_data=(X_val, y_val),\n",
    "    epochs=EPOCHS,\n",
    "    batch_size=BATCH_SIZE,\n",
    "    class_weight=class_weight,\n",
    "    callbacks=callbacks,\n",
    "    verbose=1\n",
    ")\n",
    "print(\"\\n✅ Training complete!\")"
]

eval_source = [
    "y_pred_prob = model.predict(X_test)\n",
    "y_pred = np.argmax(y_pred_prob, axis=1)\n",
    "test_acc = accuracy_score(y_test, y_pred)\n",
    "\n",
    "print(f\"Test Accuracy: {test_acc * 100:.2f}%\")\n",
    "print(f\"\\n{classification_report(y_test, y_pred, target_names=['0 People', '1 Person', '2 People'])}\")"
]

sanity1_source = [
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
    "axes[0].axvline(1.0 / N_CLASSES, color='red', linestyle='--', label='Random Guess Boundary')\n",
    "axes[0].set_title('All Test Predictions Confidence', fontweight='bold')\n",
    "axes[0].set_xlabel('Max Predicted Probability')\n",
    "axes[0].set_ylabel('Count')\n",
    "axes[0].legend()\n",
    "\n",
    "# Per-class confidence\n",
    "for cls, color, name in [(0, '#55A868', '0 People'), (1, '#C44E52', '1 Person'), (2, '#4C72B0', '2 People')]:\n",
    "    mask = y_test == cls\n",
    "    if np.any(mask):\n",
    "        axes[1].hist(np.max(y_pred_prob[mask], axis=1), bins=20, alpha=0.6, color=color, label=name, edgecolor='black')\n",
    "axes[1].axvline(1.0 / N_CLASSES, color='red', linestyle='--')\n",
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

sanity2_source = [
    "print(\"=\" * 60)\n",
    "print(\"  SANITY CHECK 2: Shuffled Labels Test\")\n",
    "print(\"=\" * 60)\n",
    "print(\"Train on RANDOM labels. If accuracy is still high, the model\")\n",
    "print(\"is memorizing data patterns, not learning the label signal.\\n\")\n",
    "\n",
    "# Shuffle labels\n",
    "y_train_shuffled = y_train.copy()\n",
    "np.random.seed(42)\n",
    "np.random.shuffle(y_train_shuffled)\n",
    "\n",
    "# Train a fresh model on shuffled labels\n",
    "model_shuffled = build_1d_cnn(X_train.shape[1:])\n",
    "model_shuffled.fit(\n",
    "    X_train, y_train_shuffled,\n",
    "    validation_data=(X_val, y_val),\n",
    "    epochs=15,\n",
    "    batch_size=BATCH_SIZE,\n",
    "    verbose=0\n",
    ")\n",
    "\n",
    "y_pred_shuffled = np.argmax(model_shuffled.predict(X_test), axis=1)\n",
    "shuffled_acc = accuracy_score(y_test, y_pred_shuffled)\n",
    "\n",
    "print(f\"Real labels accuracy:     {test_acc * 100:.2f}%\")\n",
    "print(f\"Shuffled labels accuracy: {shuffled_acc * 100:.2f}%\")\n",
    "majority_class_pct = max([np.mean(y_test == c) for c in range(N_CLASSES)]) * 100\n",
    "print(f\"Random baseline:          {majority_class_pct:.1f}% (majority class)\")\n",
    "\n",
    "if shuffled_acc > (majority_class_pct / 100.0 + 0.15):\n",
    "    print(\"\\n❌ WARNING: Shuffled model also scores high!\")\n",
    "    print(\"   The model may be exploiting data artifacts, not true label signal.\")\n",
    "else:\n",
    "    print(\"\\n✅ PASS: Shuffled model performs near chance level.\")\n",
    "    print(\"   The real model IS learning from true label differences.\")"
]

sanity3_source = [
    "print(\"=\" * 60)\n",
    "print(\"  SANITY CHECK 3: Leave-One-File-Out Cross-Validation\")\n",
    "print(\"=\" * 60)\n",
    "print(\"Train on all files except one, test on the held-out file.\")\n",
    "print(\"Repeat for every file. This is the most rigorous evaluation.\\n\")\n",
    "\n",
    "unique_file_ids = np.unique(groups)\n",
    "lofo_accuracies = []\n",
    "lofo_details = []\n",
    "\n",
    "for held_out_file in unique_file_ids:\n",
    "    # Split\n",
    "    test_mask_cv = (groups == held_out_file)\n",
    "    train_mask_cv = ~test_mask_cv\n",
    "\n",
    "    X_tr = X[train_mask_cv].copy()\n",
    "    y_tr = y[train_mask_cv]\n",
    "    X_te = X[test_mask_cv].copy()\n",
    "    y_te = y[test_mask_cv]\n",
    "\n",
    "    # Normalize\n",
    "    for s in [X_tr, X_te]:\n",
    "        m = np.mean(s, axis=(1, 2), keepdims=True)\n",
    "        sd = np.std(s, axis=(1, 2), keepdims=True) + 1e-8\n",
    "        s[:] = (s - m) / sd\n",
    "\n",
    "    # Check train has all classes represented\n",
    "    if len(np.unique(y_tr)) < N_CLASSES:\n",
    "        print(f\"  File {held_out_file}: skipped (train has only {len(np.unique(y_tr))} classes)\")\n",
    "        continue\n",
    "\n",
    "    # Build & train\n",
    "    m_cv = build_1d_cnn(X_tr.shape[1:])\n",
    "    m_cv.fit(X_tr, y_tr, epochs=15, batch_size=BATCH_SIZE, verbose=0)\n",
    "\n",
    "    preds_cv = np.argmax(m_cv.predict(X_te, verbose=0), axis=1)\n",
    "    acc_cv = accuracy_score(y_te, preds_cv)\n",
    "    lofo_accuracies.append(acc_cv)\n",
    "\n",
    "    true_label = y_te[0]\n",
    "    fname = fnames[held_out_file] if held_out_file < len(fnames) else f\"file_{held_out_file}\"\n",
    "    lofo_details.append((held_out_file, fname, true_label, len(y_te), acc_cv))\n",
    "    print(f\"  File {held_out_file} ({fname}): class={true_label}, \"\n",
    "          f\"windows={len(y_te)}, acc={acc_cv*100:.1f}%\")\n",
    "\n",
    "    # Clean up\n",
    "    del m_cv\n",
    "    keras.backend.clear_session()\n",
    "\n",
    "mean_acc = np.mean(lofo_accuracies)\n",
    "std_acc = np.std(lofo_accuracies)\n",
    "print(f\"\\n{'='*60}\")\n",
    "print(f\"  LOFO Mean Accuracy: {mean_acc*100:.2f}% ± {std_acc*100:.2f}%\")\n",
    "print(f\"{'='*60}\")\n",
    "\n",
    "if mean_acc >= 0.90:\n",
    "    print(\"\\n✅ Result: Strong performance with realistic evaluation.\")\n",
    "else:\n",
    "    print(\"\\n⚠️  Result: Previous 100% was likely inflated. This is the real accuracy.\")"
]

viz_source = [
    "class_names = ['0 People', '1 Person', '2 People']\n",
    "\n",
    "fig, axes = plt.subplots(2, 2, figsize=(14, 10))\n",
    "\n",
    "# 1. Training curves\n",
    "axes[0, 0].plot(history.history['accuracy'], label='Train', linewidth=2)\n",
    "axes[0, 0].plot(history.history['val_accuracy'], label='Val', linewidth=2)\n",
    "axes[0, 0].set_title('Accuracy over Epochs', fontsize=13, fontweight='bold')\n",
    "axes[0, 0].set_xlabel('Epoch')\n",
    "axes[0, 0].set_ylabel('Accuracy')\n",
    "axes[0, 0].legend()\n",
    "axes[0, 0].grid(True, alpha=0.3)\n",
    "\n",
    "# 2. Loss curves\n",
    "axes[0, 1].plot(history.history['loss'], label='Train', linewidth=2)\n",
    "axes[0, 1].plot(history.history['val_loss'], label='Val', linewidth=2)\n",
    "axes[0, 1].set_title('Loss over Epochs', fontsize=13, fontweight='bold')\n",
    "axes[0, 1].set_xlabel('Epoch')\n",
    "axes[0, 1].set_ylabel('Loss')\n",
    "axes[0, 1].legend()\n",
    "axes[0, 1].grid(True, alpha=0.3)\n",
    "\n",
    "# 3. Confusion Matrix\n",
    "cm = confusion_matrix(y_test, y_pred)\n",
    "disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=class_names)\n",
    "disp.plot(ax=axes[1, 0], cmap='Blues', colorbar=False)\n",
    "axes[1, 0].set_title('Confusion Matrix', fontsize=13, fontweight='bold')\n",
    "\n",
    "# 4. LOFO Cross-Validation per file\n",
    "if lofo_details:\n",
    "    file_ids = [d[0] for d in lofo_details]\n",
    "    accs = [d[4] * 100 for d in lofo_details]\n",
    "    # Color coding based on true label (0, 1, 2)\n",
    "    colors = ['#55A868' if d[2] == 0 else ('#C44E52' if d[2] == 1 else '#4C72B0') for d in lofo_details]\n",
    "    axes[1, 1].bar(range(len(accs)), accs, color=colors, edgecolor='black', alpha=0.8)\n",
    "    axes[1, 1].set_xticks(range(len(accs)))\n",
    "    axes[1, 1].set_xticklabels([f'F{fid}' for fid in file_ids], fontsize=8)\n",
    "    axes[1, 1].set_ylim(0, 110)\n",
    "    axes[1, 1].axhline(mean_acc * 100, color='navy', linestyle='--', \n",
    "                        label=f'Mean: {mean_acc*100:.1f}%')\n",
    "    axes[1, 1].set_title('Leave-One-File-Out Accuracy', fontsize=13, fontweight='bold')\n",
    "    axes[1, 1].set_xlabel('Held-out File')\n",
    "    axes[1, 1].set_ylabel('Accuracy (%)')\n",
    "    axes[1, 1].legend()\n",
    "    # Legend for colors\n",
    "    from matplotlib.patches import Patch\n",
    "    axes[1, 1].legend(handles=[\n",
    "        Patch(color='#55A868', label='0 People'),\n",
    "        Patch(color='#C44E52', label='1 Person'),\n",
    "        Patch(color='#4C72B0', label='2 People'),\n",
    "        plt.Line2D([0],[0], color='navy', linestyle='--', label=f'Mean: {mean_acc*100:.1f}%')\n",
    "    ], fontsize=9)\n",
    "\n",
    "plt.suptitle(f'1D-CNN Results | Test: {test_acc*100:.1f}% | LOFO: {mean_acc*100:.1f}% ± {std_acc*100:.1f}%', \n",
    "             fontsize=14, fontweight='bold')\n",
    "plt.tight_layout()\n",
    "plt.show()"
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
        elif 'def load_new_radar_dataset' in source_str:
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
            
        # Match Training cell
        elif 'class_weight = {' in source_str and 'callbacks = [' in source_str:
            print("Updating Model Training cell...")
            cell['source'] = train_source
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
            cell['source'] = sanity1_source
            cell['outputs'] = []
            cell['execution_count'] = None

        # Match Sanity Check 2 cell
        elif 'SANITY CHECK 2: Shuffled Labels Test' in source_str:
            print("Updating Sanity Check 2 cell...")
            cell['source'] = sanity2_source
            cell['outputs'] = []
            cell['execution_count'] = None

        # Match Sanity Check 3 cell
        elif 'SANITY CHECK 3: Leave-One-File-Out Cross-Validation' in source_str:
            print("Updating Sanity Check 3 cell...")
            cell['source'] = sanity3_source
            cell['outputs'] = []
            cell['execution_count'] = None

        # Match Visualization cell
        elif 'ConfusionMatrixDisplay(confusion_matrix=cm' in source_str:
            print("Updating Visualizations cell...")
            cell['source'] = viz_source
            cell['outputs'] = []
            cell['execution_count'] = None

# Save updated notebook
with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Altered notebook successfully!")
