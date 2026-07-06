import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
import os
import time
import copy

# ==========================================
# COUNTERFEIT CURRENCY TRAINING SCRIPT
# Architecture: MobileNet_v3_small
# ==========================================

def train_model():
    """
    Trains the Rakshak-Vision PyTorch model on a dataset of Real vs Fake currency.
    Expects a dataset folder structure like:
    dataset/
      ├── train/
      │     ├── genuine/
      │     └── counterfeit/
      └── val/
            ├── genuine/
            └── counterfeit/
    """
    
    # Configuration
    data_dir = "./dataset"
    batch_size = 32
    num_epochs = 15
    learning_rate = 0.001
    num_classes = 2  # Genuine (0), Counterfeit (1)
    
    print("Initializing Rakshak-Vision Counterfeit Training Pipeline...")
    
    if not os.path.exists(data_dir):
        print(f"[!] Dataset directory '{data_dir}' not found.")
        print("[!] Please acquire the dataset and place it in the required structure.")
        # return # Commented out for demonstration purposes
        
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # 1. Data Augmentation and Normalization
    # We use heavy augmentation to simulate real-world mobile captures (blur, rotation, color jitter)
    data_transforms = {
        'train': transforms.Compose([
            transforms.RandomResizedCrop(224),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
        'val': transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
    }

    print("Setting up DataLoaders...")
    try:
        image_datasets = {x: datasets.ImageFolder(os.path.join(data_dir, x), data_transforms[x])
                          for x in ['train', 'val']}
        dataloaders = {x: DataLoader(image_datasets[x], batch_size=batch_size, shuffle=True, num_workers=4)
                       for x in ['train', 'val']}
        dataset_sizes = {x: len(image_datasets[x]) for x in ['train', 'val']}
        class_names = image_datasets['train'].classes
    except Exception as e:
        print(f"[!] Warning: Data loading failed (likely missing directory): {e}")
        print("[!] Proceeding with model initialization only for demonstration.")
        dataset_sizes = {'train': 0, 'val': 0}
        class_names = ['genuine', 'counterfeit']

    # 2. Model Architecture
    # We use MobileNetV3-Small because it is highly optimized for edge/offline inference
    print("Loading pre-trained MobileNetV3-Small architecture...")
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    
    # Freeze the feature extraction layers (optional, but good for small datasets)
    # for param in model.parameters():
    #     param.requires_grad = False
        
    # Replace the final classification head
    num_ftrs = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(num_ftrs, num_classes)
    
    model = model.to(device)

    # 3. Loss Function and Optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1)

    # 4. Training Loop (Simulated if dataset is missing)
    if dataset_sizes['train'] > 0:
        print("Starting training loop...")
        best_model_wts = copy.deepcopy(model.state_dict())
        best_acc = 0.0

        for epoch in range(num_epochs):
            print(f'Epoch {epoch}/{num_epochs - 1}')
            print('-' * 10)

            for phase in ['train', 'val']:
                if phase == 'train':
                    model.train()
                else:
                    model.eval()

                running_loss = 0.0
                running_corrects = 0

                for inputs, labels in dataloaders[phase]:
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

                if phase == 'train':
                    scheduler.step()

                epoch_loss = running_loss / dataset_sizes[phase]
                epoch_acc = running_corrects.double() / dataset_sizes[phase]

                print(f'{phase} Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')

                if phase == 'val' and epoch_acc > best_acc:
                    best_acc = epoch_acc
                    best_model_wts = copy.deepcopy(model.state_dict())

        print(f'Best val Acc: {best_acc:4f}')
        model.load_state_dict(best_model_wts)
        
        # 5. Save the trained weights
        save_path = "../counterfeit_model.pt"
        torch.save(model.state_dict(), save_path)
        print(f"Model saved successfully to {os.path.abspath(save_path)}")
    else:
        print("[!] Training loop skipped. Model architecture is ready.")
        
if __name__ == "__main__":
    train_model()
