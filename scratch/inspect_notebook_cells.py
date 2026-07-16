import json

notebook_path = r'c:\RR_02\Human_sensing_1D_CNN.ipynb'

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for idx, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        src = "".join(cell['source'])
        print(f"Cell {idx}: Length={len(src)} | Start={src[:50].replace(chr(10), ' ')}")
