import json

notebook_path = r'c:\RR_02\Human_sensing_1D_CNN.ipynb'

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

updated = False

# Iterate through cells to find load_new_radar_dataset definition
for idx, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = cell['source']
        source_str = "".join(source)
        if 'def load_new_radar_dataset' in source_str:
            print(f"Found Data Loader in Cell {idx}. Modifying the window extraction loop...")
            
            # We want to replace the non-overlapping window loop with overlapping loop:
            # We'll build the new loader source lines
            new_source = []
            skip = False
            for line in source:
                # When we hit the sliding window loop block, we skip the old lines and insert the new ones
                if 'Extract sliding windows' in line:
                    new_source.append("                # Extract sliding windows with 80% overlap (stride = 20)\n")
                    new_source.append("                windows_added = 0\n")
                    new_source.append("                stride = 20\n")
                    new_source.append("                for i in range(0, radar_signal.shape[0] - window_size + 1, stride):\n")
                    new_source.append("                    X_raw.append(radar_signal[i : i + window_size, :])\n")
                    new_source.append("                    y_labels.append(label)\n")
                    new_source.append("                    file_groups.append(file_id)\n")
                    new_source.append("                    windows_added += 1\n")
                    skip = True
                    continue
                
                # Turn off skipping once we hit the end of that loop block
                if skip and 'if windows_added > 0:' in line:
                    skip = False
                
                if not skip:
                    new_source.append(line)
            
            cell['source'] = new_source
            cell['outputs'] = []
            cell['execution_count'] = None
            updated = True
            break

if updated:
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)
    print("Notebook updated successfully with overlapping sliding windows (stride = 20)!")
else:
    print("Could not find load_new_radar_dataset function in notebook.")
