import os
import pandas as pd
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from transformers import DistilBertModel, DistilBertTokenizer, get_linear_schedule_with_warmup
from torch.optim import AdamW
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import numpy as np

# Configuration
MODEL_NAME = "distilbert-base-multilingual-cased"
BATCH_SIZE = 16
EPOCHS = 3
MAX_LEN = 128
LEARNING_RATE = 2e-5

class RakshakMultiTaskModel(nn.Module):
    def __init__(self, num_threat_classes, num_behavior_labels):
        super(RakshakMultiTaskModel, self).__init__()
        self.bert = DistilBertModel.from_pretrained(MODEL_NAME)
        self.drop = nn.Dropout(p=0.3)
        # Head 1: Multi-class Threat Classification
        self.threat_classifier = nn.Linear(self.bert.config.hidden_size, num_threat_classes)
        # Head 2: Multi-label Behavior Classification
        self.behavior_classifier = nn.Linear(self.bert.config.hidden_size, num_behavior_labels)
        
    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs.last_hidden_state[:, 0]  # CLS token representation
        output = self.drop(pooled_output)
        
        threat_logits = self.threat_classifier(output)
        behavior_logits = self.behavior_classifier(output)
        return threat_logits, behavior_logits

class DRIDDataset(Dataset):
    def __init__(self, texts, threat_labels, behavior_labels, tokenizer, max_len):
        self.texts = texts
        self.threat_labels = threat_labels
        self.behavior_labels = behavior_labels
        self.tokenizer = tokenizer
        self.max_len = max_len
        
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, item):
        text = str(self.texts[item])
        threat = self.threat_labels[item]
        behaviors = self.behavior_labels[item]
        
        encoding = self.tokenizer(
            text, add_special_tokens=True, max_length=self.max_len,
            return_token_type_ids=False, padding='max_length',
            truncation=True, return_attention_mask=True, return_tensors='pt'
        )
        
        return {
            'text': text,
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'threat_label': torch.tensor(threat, dtype=torch.long),
            'behavior_labels': torch.tensor(behaviors, dtype=torch.float)
        }

def train_epoch(model, data_loader, loss_fn_threat, loss_fn_behaviors, optimizer, device, scheduler, n_examples):
    model = model.train()
    total_loss = 0
    
    for d in data_loader:
        input_ids = d["input_ids"].to(device)
        attention_mask = d["attention_mask"].to(device)
        threat_labels = d["threat_label"].to(device)
        behavior_labels = d["behavior_labels"].to(device)
        
        threat_logits, behavior_logits = model(input_ids=input_ids, attention_mask=attention_mask)
        
        loss_threat = loss_fn_threat(threat_logits, threat_labels)
        loss_behavior = loss_fn_behaviors(behavior_logits, behavior_labels)
        loss = loss_threat + loss_behavior  # Joint loss
        
        total_loss += loss.item()
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad()
        
    return total_loss / n_examples

if __name__ == "__main__":
    print("CUDA Available:", torch.cuda.is_available())
    device = torch.device('cpu')
    print(f"Using device: {device}")
    
    # 1. Load Data
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "drid_train.csv")
    df = pd.read_csv(data_path)
    
    # 2. Encode Labels
    le = LabelEncoder()
    df['threat_class_encoded'] = le.fit_transform(df['threat_class'])
    behavior_cols = ['bh_impersonation', 'bh_urgency', 'bh_fear', 'bh_otp', 'bh_remote']
    
    # Save label encoder mapping
    np.save(os.path.join(os.path.dirname(__file__), "..", "models", "registry", "threat_classes.npy"), le.classes_)
    
    # 3. Split Data
    df_train, df_val = train_test_split(df, test_size=0.1, random_state=42)
    
    tokenizer = DistilBertTokenizer.from_pretrained(MODEL_NAME)
    
    train_dataset = DRIDDataset(
        texts=df_train.text.to_numpy(),
        threat_labels=df_train.threat_class_encoded.to_numpy(),
        behavior_labels=df_train[behavior_cols].to_numpy(),
        tokenizer=tokenizer,
        max_len=MAX_LEN
    )
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    
    # 4. Initialize Model
    model = RakshakMultiTaskModel(num_threat_classes=len(le.classes_), num_behavior_labels=len(behavior_cols))
    model = model.to(device)
    
    # 5. Training Setup
    optimizer = AdamW(model.parameters(), lr=LEARNING_RATE)
    total_steps = len(train_loader) * EPOCHS
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=0, num_training_steps=total_steps)
    
    loss_fn_threat = nn.CrossEntropyLoss().to(device)
    loss_fn_behaviors = nn.BCEWithLogitsLoss().to(device)
    
    # 6. Train Loop
    print("Starting Training...")
    for epoch in range(EPOCHS):
        print(f"Epoch {epoch + 1}/{EPOCHS}")
        train_loss = train_epoch(model, train_loader, loss_fn_threat, loss_fn_behaviors, optimizer, device, scheduler, len(df_train))
        print(f"Train Loss: {train_loss}")
        
    # 7. Save Model
    save_dir = os.path.join(os.path.dirname(__file__), "..", "models", "rakshak-core", "v1.0")
    os.makedirs(save_dir, exist_ok=True)
    
    print(f"Saving final model to {save_dir}...")
    torch.save(model.state_dict(), os.path.join(save_dir, "pytorch_model.bin"))
    tokenizer.save_pretrained(save_dir)
    print("Training complete! Model is ready for deployment in RAIC.")
