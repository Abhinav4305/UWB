import json

notebook_path = r'c:\RR_02\Human_sensing_1D_CNN.ipynb'

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

updated = False
# Find the cell containing the configuration
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = cell['source']
        for i, line in enumerate(source):
            if 'EPOCHS =' in line:
                # Keep the newline character if it exists
                suffix = '\n' if line.endswith('\n') else ''
                source[i] = f"EPOCHS = 50{suffix}"
                updated = True
                print(f"Replacing line: {line.strip()} -> {source[i].strip()}")
                break
        if updated:
            break

if updated:
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)
    print("Notebook epochs updated to 50 successfully!")
else:
    print("Could not find EPOCHS definition in notebook!")
