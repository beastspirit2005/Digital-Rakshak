import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import XLMRobertaTokenizer, XLMRobertaForSequenceClassification
from torch.optim import AdamW
import os

# 1. Configuration
DATA_PATH = "data/drid_train.csv"
MODEL_SAVE_DIR = "models/rakshak-core/v1.0"
EPOCHS = 1
BATCH_SIZE = 8
LR = 2e-5

# The classes we use in ml_client.py
CLASSES = ["Safe", "Banking Fraud", "UPI Fraud", "Courier Scam", "Digital Arrest"]

class FraudDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len=128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, item):
        text = str(self.texts[item])
        label = self.labels[item]

        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            return_token_type_ids=False,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt',
        )

        return {
            'text': text,
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

def train_model():
    print("Starting Native PyTorch Training...")
    
    # 2. Load Data
    df = pd.read_csv(DATA_PATH)
    
    # Map string categories to integers
    label_map = {c: i for i, c in enumerate(CLASSES)}
    df['label_id'] = df['threat_class'].map(label_map).fillna(0).astype(int)
    
    tokenizer = XLMRobertaTokenizer.from_pretrained('xlm-roberta-base')
    
    dataset = FraudDataset(
        texts=df.text.to_numpy(),
        labels=df.label_id.to_numpy(),
        tokenizer=tokenizer
    )
    
    data_loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)
    
    # 3. Initialize Model
    # Forcing CPU because the installed PyTorch doesn't support RTX 5060 (sm_120) architecture yet
    device = torch.device("cpu")
    print(f"Using device: {device}")
    
    # In a real scenario, we'd use a custom architecture for multi-task (Threat + Behaviors).
    # For this hackathon training run, we will train the base sequence classifier.
    model = XLMRobertaForSequenceClassification.from_pretrained(
        'xlm-roberta-base', 
        num_labels=len(CLASSES)
    )
    model = model.to(device)
    
    optimizer = AdamW(model.parameters(), lr=LR)
    
    # 4. Training Loop
    model.train()
    for epoch in range(EPOCHS):
        total_loss = 0
        for batch_idx, batch in enumerate(data_loader):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)
            
            optimizer.zero_grad()
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )
            
            loss = outputs.loss
            total_loss += loss.item()
            
            loss.backward()
            optimizer.step()
            
            if batch_idx % 5 == 0:
                print(f"Epoch {epoch+1}/{EPOCHS} | Batch {batch_idx}/{len(data_loader)} | Loss: {loss.item():.4f}")
                
        avg_loss = total_loss / len(data_loader)
        print(f"Epoch {epoch+1} completed. Average Loss: {avg_loss:.4f}")
        
    # 5. Save Model
    print("Saving fine-tuned weights...")
    os.makedirs(MODEL_SAVE_DIR, exist_ok=True)
    torch.save(model.state_dict(), os.path.join(MODEL_SAVE_DIR, "pytorch_model.bin"))
    tokenizer.save_pretrained(MODEL_SAVE_DIR)
    
    print("Training Complete! Native AI is now fully operational.")

if __name__ == "__main__":
    train_model()
