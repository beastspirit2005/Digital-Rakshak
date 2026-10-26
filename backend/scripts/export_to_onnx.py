"""Export PyTorch v2.0 checkpoint to ONNX."""
import os
import sys

# Ensure UTF-8 output on Windows consoles to prevent unicode emoji print errors
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import torch
from transformers import DistilBertTokenizer
from scripts.train_rakshak_two_phase import RakshakMultiTaskModel, THREAT_CLASSES, BEHAVIOR_LABELS, MAX_LEN
MODEL_DIR = os.path.join(BASE_DIR, "models", "rakshak-core", "v2.0")
ONNX_PATH = os.path.join(MODEL_DIR, "model.onnx")

device = torch.device("cpu")
tokenizer = DistilBertTokenizer.from_pretrained(MODEL_DIR)

model = RakshakMultiTaskModel(len(THREAT_CLASSES), len(BEHAVIOR_LABELS))
model.load_state_dict(torch.load(os.path.join(MODEL_DIR, "pytorch_model.bin"), map_location=device))
model.eval()

dummy_text = "Dear Customer, INR 500 debited from your account via UPI."
dummy_inputs = tokenizer(dummy_text, return_tensors="pt", padding='max_length', max_length=MAX_LEN, truncation=True)
input_ids = dummy_inputs['input_ids'].to(device)
attention_mask = dummy_inputs['attention_mask'].to(device)

print(f"Exporting ONNX model to {ONNX_PATH}...")
torch.onnx.export(
    model,
    (input_ids, attention_mask),
    ONNX_PATH,
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

print(f"Export Complete! File size: {os.path.getsize(ONNX_PATH) / (1024*1024):.2f} MB")
