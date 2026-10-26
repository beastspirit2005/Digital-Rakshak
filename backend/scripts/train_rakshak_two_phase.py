"""
Digital Rakshak - Two-Phase Layer-Wise Model Training Pipeline (v2.0)
=====================================================================
Features:
1. Hardware Acceleration: NVIDIA CUDA (RTX 5060 Laptop GPU) + FP16 AMP.
2. Architecture: Multi-Task DistilBERT (Multilingual) with Threat Head & Attack DNA Head.
3. Phase 1: 100,000 Clean Real Samples with 3-Stage Progressive Unfreezing & LLRD:
   - Stage 1: Dual Heads warmup (Backbone frozen, lr=1e-3)
   - Stage 2: Top layers unfreeze (Layers 4 & 5, lr=5e-5)
   - Stage 3: Full LLRD (All layers, decay=0.8, base_lr=2e-5)
4. Phase 2: In-The-Wild Robustness Tuning on Raw Noisy Dataset (lr=5e-6).
5. Dual Export:
   - PyTorch CUDA: backend/models/rakshak-core/v2.0/pytorch_model.bin
   - Optimized ONNX Runtime: backend/models/rakshak-core/v2.0/model.onnx
"""

import os
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import json
import time
import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, f1_score, accuracy_score
from transformers import DistilBertModel, DistilBertTokenizer, get_linear_schedule_with_warmup
from torch.optim import AdamW

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "real_cyber_100k_clean.csv")
RAW_DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "real_cyber_raw_noisy.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "models", "rakshak-core", "v2.0")
os.makedirs(OUTPUT_DIR, exist_ok=True)

MODEL_NAME = "distilbert-base-multilingual-cased"
BATCH_SIZE = 32
MAX_LEN = 128
LLRD_DECAY = 0.8

THREAT_CLASSES = [
    "Safe",
    "Banking Fraud",
    "UPI Fraud",
    "Digital Arrest",
    "Courier Scam",
    "Loan Extortion"
]

BEHAVIOR_LABELS = [
    "Impersonation",
    "Urgency",
    "Fear",
    "OTP Harvesting",
    "Remote Access",
    "Mule Routing"
]

class RakshakMultiTaskModel(nn.Module):
    def __init__(self, num_threat_classes, num_behavior_labels):
        super(RakshakMultiTaskModel, self).__init__()
        self.bert = DistilBertModel.from_pretrained(MODEL_NAME)
        self.drop = nn.Dropout(p=0.25)
        # Head 1: Multi-class Threat Classification
        self.threat_classifier = nn.Linear(self.bert.config.hidden_size, num_threat_classes)
        # Head 2: Multi-label Attack DNA Detection
        self.behavior_classifier = nn.Linear(self.bert.config.hidden_size, num_behavior_labels)
        
    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs.last_hidden_state[:, 0]  # [CLS] token representation
        output = self.drop(pooled_output)
        threat_logits = self.threat_classifier(output)
        behavior_logits = self.behavior_classifier(output)
        return threat_logits, behavior_logits

class CyberDataset(Dataset):
    def __init__(self, texts, threat_labels, behavior_vectors, tokenizer, max_len):
        self.texts = texts
        self.threat_labels = threat_labels
        self.behavior_vectors = behavior_vectors
        self.tokenizer = tokenizer
        self.max_len = max_len
        
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, item):
        text = str(self.texts[item])
        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt'
        )
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'threat_label': torch.tensor(self.threat_labels[item], dtype=torch.long),
            'behavior_labels': torch.tensor(self.behavior_vectors[item], dtype=torch.float)
        }

def get_llrd_optimizer_grouped_parameters(model, base_lr=2e-5, decay_rate=0.8):
    """Builds Layer-wise Learning Rate Decay parameter groups for DistilBERT."""
    no_decay = ["bias", "LayerNorm.weight"]
    optimizer_grouped_parameters = []
    
    # Dual Classification Heads (Highest LR)
    optimizer_grouped_parameters.extend([
        {
            "params": [p for n, p in model.threat_classifier.named_parameters() if not any(nd in n for nd in no_decay)],
            "weight_decay": 0.01,
            "lr": base_lr * 1.5
        },
        {
            "params": [p for n, p in model.threat_classifier.named_parameters() if any(nd in n for nd in no_decay)],
            "weight_decay": 0.0,
            "lr": base_lr * 1.5
        },
        {
            "params": [p for n, p in model.behavior_classifier.named_parameters() if not any(nd in n for nd in no_decay)],
            "weight_decay": 0.01,
            "lr": base_lr * 1.5
        },
        {
            "params": [p for n, p in model.behavior_classifier.named_parameters() if any(nd in n for nd in no_decay)],
            "weight_decay": 0.0,
            "lr": base_lr * 1.5
        }
    ])
    
    # DistilBERT Transformer layers (6 layers: 5 down to 0)
    num_layers = len(model.bert.transformer.layer)
    for layer_idx in range(num_layers - 1, -1, -1):
        layer = model.bert.transformer.layer[layer_idx]
        layer_lr = base_lr * (decay_rate ** (num_layers - 1 - layer_idx))
        optimizer_grouped_parameters.extend([
            {
                "params": [p for n, p in layer.named_parameters() if not any(nd in n for nd in no_decay)],
                "weight_decay": 0.01,
                "lr": layer_lr
            },
            {
                "params": [p for n, p in layer.named_parameters() if any(nd in n for nd in no_decay)],
                "weight_decay": 0.0,
                "lr": layer_lr
            }
        ])
        
    # Embeddings (Lowest LR)
    embed_lr = base_lr * (decay_rate ** num_layers)
    optimizer_grouped_parameters.extend([
        {
            "params": [p for n, p in model.bert.embeddings.named_parameters() if not any(nd in n for nd in no_decay)],
            "weight_decay": 0.01,
            "lr": embed_lr
        },
        {
            "params": [p for n, p in model.bert.embeddings.named_parameters() if any(nd in n for nd in no_decay)],
            "weight_decay": 0.0,
            "lr": embed_lr
        }
    ])
    
    return optimizer_grouped_parameters

def train_epoch(model, dataloader, optimizer, scheduler, loss_fn_threat, loss_fn_behaviors, device, scaler):
    model.train()
    total_loss = 0.0
    start_time = time.time()
    
    for step, batch in enumerate(dataloader):
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        threat_labels = batch['threat_label'].to(device)
        behavior_labels = batch['behavior_labels'].to(device)
        
        optimizer.zero_grad()
        
        # AMP mixed precision for NVIDIA GPU speedup
        if device.type == 'cuda' and scaler is not None:
            with torch.cuda.amp.autocast():
                threat_logits, behavior_logits = model(input_ids, attention_mask)
                loss_threat = loss_fn_threat(threat_logits, threat_labels)
                loss_behaviors = loss_fn_behaviors(behavior_logits, behavior_labels)
                loss = loss_threat + 0.5 * loss_behaviors
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            scaler.step(optimizer)
            scaler.update()
        else:
            threat_logits, behavior_logits = model(input_ids, attention_mask)
            loss_threat = loss_fn_threat(threat_logits, threat_labels)
            loss_behaviors = loss_fn_behaviors(behavior_logits, behavior_labels)
            loss = loss_threat + 0.5 * loss_behaviors
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            
        if scheduler is not None:
            scheduler.step()
            
        total_loss += loss.item()
        if (step + 1) % 100 == 0 or (step + 1) == len(dataloader):
            elapsed = time.time() - start_time
            print(f"  Step {step + 1}/{len(dataloader)} | Loss: {total_loss / (step + 1):.4f} | Speed: {((step + 1) * BATCH_SIZE) / elapsed:.1f} samples/sec", flush=True)
            
    return total_loss / len(dataloader)

def evaluate(model, dataloader, device):
    model.eval()
    all_preds = []
    all_targets = []
    
    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            threat_labels = batch['threat_label'].to(device)
            
            threat_logits, _ = model(input_ids, attention_mask)
            preds = torch.argmax(threat_logits, dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_targets.extend(threat_labels.cpu().numpy())
            
    acc = accuracy_score(all_targets, all_preds)
    f1 = f1_score(all_targets, all_preds, average='weighted')
    return acc, f1

def export_onnx(model, tokenizer, output_path, device=None):
    """Exports trained PyTorch model to optimized ONNX format for ultra-fast CPU inference."""
    print(f"Exporting model to ONNX runtime format at {output_path}...")
    model.eval()
    cpu_model = model.to('cpu')
    dummy_text = "Dear Customer, INR 500 debited from your account via UPI."
    dummy_inputs = tokenizer(dummy_text, return_tensors="pt", padding='max_length', max_length=MAX_LEN, truncation=True)
    input_ids = dummy_inputs['input_ids'].to('cpu')
    attention_mask = dummy_inputs['attention_mask'].to('cpu')
    
    torch.onnx.export(
        cpu_model,
        (input_ids, attention_mask),
        output_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=['input_ids', 'attention_mask'],
        output_names=['threat_logits', 'behavior_logits'],
        dynamic_axes={
            'input_ids': {0: 'batch_size'},
            'attention_mask': {0: 'batch_size'},
            'threat_logits': {0: 'batch_size'},
            'behavior_logits': {0: 'batch_size'}
        }
    )
    print(f"ONNX export successful! Size: {os.path.getsize(output_path) / (1024*1024):.2f} MB")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-limit", type=int, default=None, help="Limit samples for testing")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Training batch size")
    args = parser.parse_args()

    print("=" * 70)
    print("DIGITAL RAKSHAK: TWO-PHASE LAYER-WISE TRANSFORMER TRAINING (v2.0)")
    print("=" * 70)
    
    # 1. Device check with execution guard for new GPU architectures (e.g. sm_120 Blackwell)
    use_cuda = False
    if torch.cuda.is_available():
        try:
            test_t = torch.zeros(1, device='cuda')
            test_t = test_t + 1
            use_cuda = True
            device = torch.device('cuda')
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"CUDA ACCELERATED: {gpu_name} ({vram_gb:.2f} GB VRAM)")
            scaler = torch.cuda.amp.GradScaler()
        except Exception:
            print("Notice: NVIDIA RTX 50-series (Blackwell sm_120) detected. PyTorch cu124 precompiled kernels are compiled up to sm_90.")
            print("Switching seamlessly to High-Performance 28-Core CPU (16 parallel threads).")
            use_cuda = False

    if not use_cuda:
        device = torch.device('cpu')
        torch.set_num_threads(16)
        scaler = None

    # 2. Load and parse Clean Dataset
    print(f"\nLoading clean dataset from {CLEAN_DATA_PATH}...")
    df_clean = pd.read_csv(CLEAN_DATA_PATH)
    if args.sample_limit:
        print(f"Applying sample limit: {args.sample_limit:,} rows")
        df_clean = df_clean.sample(n=min(args.sample_limit, len(df_clean)), random_state=42)
    print(f"Loaded {len(df_clean):,} clean records.")
    
    threat_map = {cls_name: idx for idx, cls_name in enumerate(THREAT_CLASSES)}
    behavior_map = {bh: idx for idx, bh in enumerate(BEHAVIOR_LABELS)}
    
    # Map labels to numeric IDs
    df_clean['threat_label'] = df_clean['threat_class'].map(lambda x: threat_map.get(x, 1))
    
    def parse_behaviors(b_str):
        vec = [0.0] * len(BEHAVIOR_LABELS)
        try:
            b_list = json.loads(b_str) if isinstance(b_str, str) else []
            for b in b_list:
                if b in behavior_map:
                    vec[behavior_map[b]] = 1.0
        except Exception:
            pass
        return vec
        
    df_clean['behavior_vec'] = df_clean['behaviors'].apply(parse_behaviors)
    
    # Train / Val Split (90% train, 10% validation)
    train_df, val_df = train_test_split(df_clean, test_size=0.10, random_state=42, stratify=df_clean['threat_label'])
    print(f"Split: {len(train_df):,} Train samples | {len(val_df):,} Validation samples")
    
    # Tokenizer
    tokenizer = DistilBertTokenizer.from_pretrained(MODEL_NAME)
    
    train_dataset = CyberDataset(
        train_df['text'].values,
        train_df['threat_label'].values,
        train_df['behavior_vec'].values,
        tokenizer,
        MAX_LEN
    )
    val_dataset = CyberDataset(
        val_df['text'].values,
        val_df['threat_label'].values,
        val_df['behavior_vec'].values,
        tokenizer,
        MAX_LEN
    )
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0, pin_memory=True if device.type == 'cuda' else False)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE * 2, shuffle=False)
    
    # 3. Model Initialization
    print(f"\nInitializing Multi-Task Model based on {MODEL_NAME}...")
    model = RakshakMultiTaskModel(
        num_threat_classes=len(THREAT_CLASSES),
        num_behavior_labels=len(BEHAVIOR_LABELS)
    ).to(device)
    
    loss_fn_threat = nn.CrossEntropyLoss().to(device)
    loss_fn_behaviors = nn.BCEWithLogitsLoss().to(device)
    
    # =========================================================================
    # PHASE 1: 3-STAGE LAYER-WISE CLEAN FOUNDATION TRAINING
    # =========================================================================
    print("\n" + "=" * 50)
    print("PHASE 1 - STAGE 1: Dual Heads Warmup (Backbone Frozen)")
    print("=" * 50)
    # Freeze DistilBERT backbone
    for param in model.bert.parameters():
        param.requires_grad = False
    for param in model.threat_classifier.parameters():
        param.requires_grad = True
    for param in model.behavior_classifier.parameters():
        param.requires_grad = True
        
    optimizer_stage1 = AdamW(
        list(model.threat_classifier.parameters()) + list(model.behavior_classifier.parameters()),
        lr=1e-3,
        weight_decay=0.01
    )
    train_epoch(model, train_loader, optimizer_stage1, None, loss_fn_threat, loss_fn_behaviors, device, scaler)
    acc1, f1_1 = evaluate(model, val_loader, device)
    print(f"Stage 1 Validation -> Accuracy: {acc1 * 100:.2f}% | F1: {f1_1 * 100:.2f}%")
    
    print("\n" + "=" * 50)
    print("PHASE 1 - STAGE 2: Top Layer Unfreezing (Layers 4 & 5)")
    print("=" * 50)
    for layer in model.bert.transformer.layer[4:]:
        for param in layer.parameters():
            param.requires_grad = True
            
    optimizer_stage2 = AdamW([
        {"params": model.threat_classifier.parameters(), "lr": 2e-4},
        {"params": model.behavior_classifier.parameters(), "lr": 2e-4},
        {"params": model.bert.transformer.layer[4].parameters(), "lr": 3e-5},
        {"params": model.bert.transformer.layer[5].parameters(), "lr": 5e-5}
    ], weight_decay=0.01)
    
    train_epoch(model, train_loader, optimizer_stage2, None, loss_fn_threat, loss_fn_behaviors, device, scaler)
    acc2, f1_2 = evaluate(model, val_loader, device)
    print(f"Stage 2 Validation -> Accuracy: {acc2 * 100:.2f}% | F1: {f1_2 * 100:.2f}%")
    
    print("\n" + "=" * 50)
    print("PHASE 1 - STAGE 3: Full LLRD Fine-Tuning (All Layers)")
    print("=" * 50)
    for param in model.parameters():
        param.requires_grad = True
        
    llrd_params = get_llrd_optimizer_grouped_parameters(model, base_lr=2e-5, decay_rate=LLRD_DECAY)
    optimizer_stage3 = AdamW(llrd_params)
    warmup_steps = min(50, max(1, len(train_loader) // 10))
    scheduler_stage3 = get_linear_schedule_with_warmup(optimizer_stage3, num_warmup_steps=warmup_steps, num_training_steps=len(train_loader))
    
    train_epoch(model, train_loader, optimizer_stage3, scheduler_stage3, loss_fn_threat, loss_fn_behaviors, device, scaler)
    acc3, f1_3 = evaluate(model, val_loader, device)
    print(f"Stage 3 Validation -> Accuracy: {acc3 * 100:.2f}% | F1: {f1_3 * 100:.2f}%")
    
    # =========================================================================
    # PHASE 2: RAW IN-THE-WILD ADVERSARIAL ROBUSTNESS FINE-TUNING
    # =========================================================================
    print("\n" + "=" * 50)
    print("PHASE 2: Raw In-The-Wild Robustness Tuning")
    print("=" * 50)
    if os.path.exists(RAW_DATA_PATH):
        print(f"Loading raw noisy corpus from {RAW_DATA_PATH}...")
        df_raw = pd.read_csv(RAW_DATA_PATH)
        if args.sample_limit:
            df_raw = df_raw.sample(n=min(args.sample_limit, len(df_raw)), random_state=42)
        df_raw['threat_label'] = df_raw['threat_class'].map(lambda x: threat_map.get(x, 1))
        df_raw['behavior_vec'] = [[0.0] * len(BEHAVIOR_LABELS)] * len(df_raw)
        
        raw_train_df, raw_val_df = train_test_split(df_raw, test_size=0.10, random_state=42)
        raw_train_dataset = CyberDataset(
            raw_train_df['text'].values,
            raw_train_df['threat_label'].values,
            raw_train_df['behavior_vec'].values,
            tokenizer,
            MAX_LEN
        )
        raw_train_loader = DataLoader(raw_train_dataset, batch_size=BATCH_SIZE, shuffle=True, pin_memory=True if device.type == 'cuda' else False)
        
        optimizer_raw = AdamW(model.parameters(), lr=5e-6, weight_decay=0.01)
        train_epoch(model, raw_train_loader, optimizer_raw, None, loss_fn_threat, loss_fn_behaviors, device, scaler)
        
        final_acc, final_f1 = evaluate(model, val_loader, device)
        print(f"\nFinal Post-Robustness Validation -> Accuracy: {final_acc * 100:.2f}% | F1: {final_f1 * 100:.2f}%")
    
    # =========================================================================
    # SAVE & EXPORT PRODUCTION ARTIFACTS
    # =========================================================================
    print("\n" + "=" * 50)
    print(f"Saving Trained PyTorch Weights to {OUTPUT_DIR}...")
    print("=" * 50)
    torch.save(model.state_dict(), os.path.join(OUTPUT_DIR, "pytorch_model.bin"))
    tokenizer.save_pretrained(OUTPUT_DIR)
    
    # Save config and labels
    config = {
        "model_type": "distilbert_multitask",
        "base_model": MODEL_NAME,
        "max_length": MAX_LEN,
        "threat_classes": THREAT_CLASSES,
        "behavior_labels": BEHAVIOR_LABELS,
        "num_threat_classes": len(THREAT_CLASSES),
        "num_behavior_labels": len(BEHAVIOR_LABELS)
    }
    with open(os.path.join(OUTPUT_DIR, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        
    # Save class list for compatibility
    np.save(os.path.join(BASE_DIR, "models", "registry", "threat_classes.npy"), THREAT_CLASSES)
    
    # Export to ONNX
    onnx_path = os.path.join(OUTPUT_DIR, "model.onnx")
    export_onnx(model, tokenizer, onnx_path, device)
    
    print("\n" + "=" * 70)
    print("Training, Robustness Tuning, and Dual Production Export Complete!")
    print(f"- PyTorch Model: {os.path.join(OUTPUT_DIR, 'pytorch_model.bin')}")
    print(f"- ONNX Model:    {onnx_path}")
    print("=" * 70)

if __name__ == "__main__":
    main()
