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
            print(f"Found Data Loader in Cell {idx}. Modifying to add static clutter subtraction...")
            
            new_source = []
            for line in source:
                new_source.append(line)
                # We insert clutter subtraction right after computing the average across channels
                if 'radar_signal = np.mean(data_mag, axis=(1, 2))' in line:
                    new_source.append("\n")
                    new_source.append("                # Subtract static clutter (background average subtraction) over range bins\n")
                    new_source.append("                radar_signal = radar_signal - np.mean(radar_signal, axis=0, keepdims=True)\n")
            
            cell['source'] = new_source
            cell['outputs'] = []
            cell['execution_count'] = None
            updated = True
            break

if updated:
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)
    print("Notebook updated successfully with static clutter subtraction!")
else:
    print("Could not find load_new_radar_dataset function in notebook.")
