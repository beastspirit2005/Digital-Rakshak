import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader

def train_model():
    print("Initializing Rakshak Vision Training Pipeline...")
    
    # 1. Setup Directories
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.abspath(os.path.join(base_dir, "..", "..", "data", "currency"))
    model_out_dir = os.path.abspath(os.path.join(base_dir, "..", "..", "models", "rakshak-vision"))
    
    if not os.path.exists(data_dir):
        print(f"Error: Data directory not found at {data_dir}")
        print("Please extract your Kaggle dataset so it has the following structure:")
        print("  backend/data/currency/real/")
        print("  backend/data/currency/fake/")
        return
        
    os.makedirs(model_out_dir, exist_ok=True)
    model_save_path = os.path.join(model_out_dir, "counterfeit_model.pt")

    # 2. Setup Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # 3. Data Augmentation and Transforms
    print("Preparing data augmentations...")
    data_transforms = {
        'train': transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.2, contrast=0.2),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
        'val': transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
    }

    # 4. Load Dataset
    try:
        full_dataset = datasets.ImageFolder(data_dir, transform=data_transforms['train'])
    except Exception as e:
        print(f"Error loading images: {e}")
        return

    # Split 80% train, 20% validation
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(full_dataset, [train_size, val_size])
    
    # Overwrite transform for validation dataset
    val_dataset.dataset.transform = data_transforms['val']

    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False, num_workers=0)

    class_names = full_dataset.classes
    print(f"Found classes: {class_names} with {len(full_dataset)} total images.")

    # 5. Initialize Model (MobileNetV3 Small as per ml_client.py)
    print("Initializing MobileNetV3 Small architecture...")
    model = models.mobilenet_v3_small(pretrained=True)
    
    # Modify the final classification layer for 2 classes (Real vs Fake)
    num_ftrs = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(num_ftrs, len(class_names))
    model = model.to(device)

    # 6. Loss Function & Optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # 7. Training Loop
    num_epochs = 10
    print(f"Starting training for {num_epochs} epochs...")
    
    best_acc = 0.0

    for epoch in range(num_epochs):
        print(f"\nEpoch {epoch+1}/{num_epochs}")
        print("-" * 10)

        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()
                dataloader = train_loader
            else:
                model.eval()
                dataloader = val_loader

            running_loss = 0.0
            running_corrects = 0

            for inputs, labels in dataloader:
                inputs = inputs.to(device)
                labels = labels.to(device)

                optimizer.zero_grad()

                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)

                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)

            epoch_loss = running_loss / len(dataloader.dataset)
            epoch_acc = running_corrects.double() / len(dataloader.dataset)

            print(f"{phase.capitalize()} Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}")

            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                torch.save(model.state_dict(), model_save_path)
                print(f"New best model saved to {model_save_path}")

    print(f"\nTraining complete! Best Validation Accuracy: {best_acc:.4f}")
    print(f"Final weights are stored at: {model_save_path}")

if __name__ == "__main__":
    train_model()
