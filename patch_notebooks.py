import json

fp = "Human_sensing_1D_CNN.ipynb"
with open(fp, "r", encoding="utf-8") as f:
    nb = json.load(f)

for cell in nb.get("cells", []):
    if cell.get("cell_type") == "code":
        src = cell.get("source", [])
        
        # Patch N_CLASSES
        for i, line in enumerate(src):
            if "N_CLASSES = 3" in line:
                src[i] = line.replace("N_CLASSES = 3", "N_CLASSES = 6")
                print(f"Patched N_CLASSES in {fp}")
                
        # Patch categories
        for i, line in enumerate(src):
            if "'movement/2_people': 2," in line:
                # Insert the new categories right after
                src.insert(i+1, "        'movement/3_people': 3,\n")
                src.insert(i+2, "        'movement/4_people': 4,\n")
                src.insert(i+3, "        'movement/5_people': 5,\n")
                src.insert(i+4, "        'no_movement/3_people': 3,\n")
                src.insert(i+5, "        'no_movement/4_people': 4,\n")
                src.insert(i+6, "        'no_movement/5_people': 5,\n")
                print(f"Patched categories in {fp}")
                break

with open(fp, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    # Ensure it ends with a newline
    f.write("\n")
print(f"Saved {fp}")
