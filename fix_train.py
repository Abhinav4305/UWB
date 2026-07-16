import os

file_path = r"c:\RR_02\x7_train_1m.py"
with open(file_path, "r") as f:
    content = f.read()

# Replace the broken lines with the correct training loop
broken_text = """    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = GestureCNN_X7_V2(n_classes=N_CLASSES).to(device)
                    total += y.size(0)
            
            val_acc = correct / total if total > 0 else 0"""

fixed_text = """    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = GestureCNN_X7_V2(n_classes=N_CLASSES).to(device)
    crit = torch.nn.CrossEntropyLoss()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    
    try:
        best_acc = 0.0
        os.makedirs(args.out, exist_ok=True)
        for ep in range(1, args.epochs + 1):
            # Training
            model.train()
            train_dataset.dataset.augment = True
            total_loss = 0
            for x, y in train_loader:
                opt.zero_grad()
                loss = crit(model(x.to(device)), y.to(device))
                loss.backward(); opt.step()
                total_loss += loss.item()
            
            scheduler.step()
                
            # Validation
            model.eval()
            train_dataset.dataset.augment = False 
            correct, total = 0, 0
            with torch.no_grad():
                for x, y in val_loader:
                    preds = torch.argmax(model(x.to(device)), dim=1)
                    correct += (preds == y.to(device)).sum().item()
                    total += y.size(0)
            
            val_acc = correct / total if total > 0 else 0"""

content = content.replace(broken_text, fixed_text)

with open(file_path, "w") as f:
    f.write(content)
print("Fixed x7_train_1m.py")
