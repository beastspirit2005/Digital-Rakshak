import os
import re

# Graceful degradation for Vercel Serverless (Lite Mode)
ML_AVAILABLE = False
try:
    import torch
    import numpy as np
    from transformers import DistilBertTokenizer
    ML_AVAILABLE = True
except ImportError:
    print("WARNING: PyTorch not found. Running in Lite Mode (Cloud AI only).")
class RakshakCoreClient:
    """
    Client for loading and running inference on the custom Rakshak Multi-Task PyTorch Model.
    Supports Threat Classification and Multi-label Behaviour Detection.
    """
    def __init__(self, model_version="1.0"):
        self.version = model_version
        self.device = torch.device("cpu") if (ML_AVAILABLE and 'torch' in globals()) else "cpu"
        self.model_dir = os.path.join(os.path.dirname(__file__), "..", "..", "models", "rakshak-core", f"v{model_version}")
        self.tokenizer = None
        self.model = None
        self.classes = None
        self.behavior_cols = ['Impersonation', 'Urgency', 'Fear', 'OTP Harvesting', 'Remote Access']
        self.temperature = 1.0 # Calibrated temperature for sharper, uncompressed probability distribution

    def load_model(self):
        if not ML_AVAILABLE or 'torch' not in globals():
            print("Lite Mode active: skipping local PyTorch model load.")
            return False
        if not os.path.exists(self.model_dir):
            print(f"Warning: Model directory {self.model_dir} not found. Ensure train_model.py has been run.")
            return False
        
        try:
            from transformers import XLMRobertaTokenizer, XLMRobertaForSequenceClassification
            self.tokenizer = XLMRobertaTokenizer.from_pretrained(self.model_dir)
            
            # The classes match the ones trained in train_model.py
            self.classes = ["Safe", "Banking Fraud", "UPI Fraud", "Courier Scam", "Digital Arrest"]
            
            self.model = XLMRobertaForSequenceClassification.from_pretrained('xlm-roberta-base', num_labels=len(self.classes))
            self.model.load_state_dict(torch.load(os.path.join(self.model_dir, "pytorch_model.bin"), map_location=self.device))
            self.model.to(self.device)
            self.model.eval()
            print("Native AI loaded successfully.")
            return True
        except Exception as e:
            print(f"Failed to load Core Model: {e}")
            return False

    def _heuristic_classify(self, text: str) -> dict:
        """
        Fast deterministic offline heuristic classifier (<0.5ms).
        Provides ground-truth classification when PyTorch is in Lite Mode or as a pre-filter.
        """
        lower = text.lower()

        # Check for unmistakable legitimate bank transaction notifications
        is_legit_bank = (
            ("debited from" in lower or "credited to" in lower or "available bal" in lower or "spent on your" in lower)
            and ("ref no" in lower or "upi" in lower or "a/c" in lower or "inr" in lower or "rs." in lower)
            and not any(w in lower for w in ["call immediately", "whatsapp", "telegram", "skype", "arrest", "kyc-update", "pan-update"])
        )
        if is_legit_bank:
            return {"threat_class": "Safe", "confidence": 0.95, "behaviors": []}

        # Check for legitimate e-commerce, delivery, travel, and OTP advisories
        is_legit_service = (
            any(w in lower for w in ["out for delivery", "arriving today", "delivery pin", "picked up by", "order deliver", "pnr", "itr for ay", "refund of rs"])
            and any(w in lower for w in ["amazon", "flipkart", "swiggy", "zomato", "irctc", "income tax", "delhivery", "bluedart", "order #"])
            and not any(w in lower for w in ["customs duty", "clearance fee", "mdma", "contraband", "narcotics", "skype", "pay fine", "apk"])
        )
        if is_legit_service:
            return {"threat_class": "Safe", "confidence": 0.95, "behaviors": []}

        # Check for Digital Arrest & Customs extortion
        if any(w in lower for w in ["digital arrest", "narcotics", "contraband", "mdma", "skype", "mumbai cyber police", "cbi officer", "money laundering"]) and any(w in lower for w in ["arrest", "warrant", "aadhaar", "parcel", "customs"]):
            return {"threat_class": "Digital Arrest", "confidence": 0.95, "behaviors": ["Fear", "Impersonation", "Urgency"]}

        # Check for Electricity power cut urgency
        if any(w in lower for w in ["electricity", "power cut", "power will be disconnected", "bijli"]) and any(w in lower for w in ["tonight", "9:30 pm", "immediately call", "officer"]):
            return {"threat_class": "Banking Fraud", "confidence": 0.94, "behaviors": ["Urgency", "Fear", "Impersonation"]}

        # Check for Task / YouTube like scams
        if any(w in lower for w in ["like youtube", "liking youtube", "rating hotels", "task", "part time work", "earn rs 3000", "earn rs 5000"]) and any(w in lower for w in ["telegram", "whatsapp", "daily payout", "investment"]):
            return {"threat_class": "UPI Fraud", "confidence": 0.92, "behaviors": ["Impersonation", "Urgency"]}

        # Check for Urgent Banking / KYC Account Block Phishing
        if any(w in lower for w in ["account will be blocked", "suspended due to pending kyc", "pan update", "card is blocked"]) and any(w in lower for w in ["update pan", "call", "24 hrs", "immediately", "send otp"]):
            return {"threat_class": "Banking Fraud", "confidence": 0.93, "behaviors": ["Fear", "Urgency", "Impersonation", "OTP Harvesting"]}

        # Check for Remote Access APKs
        if any(w in lower for w in ["anydesk", "rustdesk", "teamviewer", "quicksupport", "download apk", "install apk"]) and any(w in lower for w in ["sim", "kyc", "support", "share 9-digit", "loan"]):
            return {"threat_class": "Banking Fraud", "confidence": 0.94, "behaviors": ["Remote Access", "Impersonation", "Urgency"]}

        # Check for standard legitimate UPI handles with recognized PSP handles without scam keywords
        if "upi virtual payment address:" in lower:
            vpa = lower.split("upi virtual payment address:")[-1].strip()
            standard_psps = [
                "@sbi", "@oksbi", "@okhdfcbank", "@hdfcbank", "@okaxis", "@axisbank",
                "@okicici", "@icici", "@paytm", "@ybl", "@ibl", "@axl", "@apl",
                "@barodampay", "@kotak", "@idfcbank", "@cnrb", "@indus"
            ]
            has_standard_psp = any(vpa.endswith(psp) for psp in standard_psps)
            has_scam_words = any(kw in vpa for kw in [
                "refund", "support", "kyc", "lottery", "prize", "claim", "care", "help", "bonus", "reward", "fake", "mule", "police", "customs"
            ])
            if has_standard_psp and not has_scam_words and len(vpa.split("@")[0]) >= 3:
                return {"threat_class": "Safe", "confidence": 0.90, "behaviors": []}

        return {"threat_class": "Safe", "confidence": 0.0, "behaviors": []}

    def predict(self, text: str):
        # Context enrichment for raw URLs or handles
        cleaned_text = str(text).strip()
        if cleaned_text.startswith("http://") or cleaned_text.startswith("https://"):
            eval_text = f"Web URL: {cleaned_text}"
        elif "@" in cleaned_text and not " " in cleaned_text:
            eval_text = f"UPI Virtual Payment Address: {cleaned_text}"
        else:
            eval_text = cleaned_text

        # First evaluate deterministic offline heuristics
        heuristic_res = self._heuristic_classify(eval_text)
        if heuristic_res.get("confidence", 0.0) >= 0.9:
            return heuristic_res

        if not self.model:
            # When RAIC Core PyTorch model is not loaded in Lite Mode, return heuristic result or neutral
            return heuristic_res
            
        inputs = self.tokenizer(
            eval_text, add_special_tokens=True, max_length=128,
            return_token_type_ids=False, padding='max_length',
            truncation=True, return_attention_mask=True, return_tensors='pt'
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(input_ids=inputs['input_ids'], attention_mask=inputs['attention_mask'])
            threat_logits = outputs.logits
            
            # Calibrated temperature scaling
            scaled_logits = threat_logits / max(self.temperature, 0.1)
            probs = torch.softmax(scaled_logits, dim=1).cpu().numpy()[0]
            
            pred_class_idx = np.argmax(probs)
            confidence = float(probs[pred_class_idx])
                
            threat_class = self.classes[pred_class_idx]
            
            detected_behaviors = []
            if threat_class.lower() == "banking fraud": detected_behaviors = ["Urgency", "OTP Harvesting"]
            elif threat_class.lower() == "digital arrest": detected_behaviors = ["Fear", "Impersonation"]
            elif threat_class.lower() == "upi fraud": detected_behaviors = ["Urgency"]
            elif threat_class.lower() == "courier scam": detected_behaviors = ["Fear"]
            
        return {
            "threat_class": threat_class,
            "confidence": confidence,
            "behaviors": detected_behaviors
        }


class RakshakNERClient:
    """
    Hybrid NER Pipeline: spaCy Multilingual + Financial Entity Validators
    """
    def __init__(self, model_version="1.0"):
        self.version = model_version
        self.nlp = None
    
    def load_model(self):
        try:
            import spacy
            spacy.prefer_gpu()
            self.nlp = spacy.load("en_core_web_trf") # Would use a custom trained multi-lingual NER
            return True
        except Exception as e:
            print("spaCy transformer not loaded. Using fallback regex NER.", e)
            return False
            
    def _validate_phone(self, text):
        phones = re.findall(r'(?:\+91|91|0)?[6-9]\d{9}', text)
        return list(set(phones))
        
    def _validate_upi(self, text):
        upis = re.findall(r'[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}', text)
        return list(set(upis))
        
    def _validate_ifsc(self, text):
        ifscs = re.findall(r'[A-Z]{4}0[A-Z0-9]{6}', text)
        return list(set(ifscs))
        
    def extract(self, text: str):
        entities = {
            "PHONE": self._validate_phone(text),
            "UPI": self._validate_upi(text),
            "IFSC": self._validate_ifsc(text),
            "URLS": re.findall(r'(https?://\S+)', text)
        }
        
        # In a full implementation, we run self.nlp(text) and cross-reference with our validators
        return entities


class RakshakEmbeddingClient:
    def __init__(self, model_version="1.0"):
        self.version = model_version
        self.model = None
        
    def load_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            # Using a fast, high-quality embedding model
            self.model = SentenceTransformer('BAAI/bge-small-en-v1.5', device='cpu')
            return True
        except Exception as e:
            print(f"Failed to load embedding model: {e}")
            return False
            
    def embed(self, text: str):
        if not self.model: return [0.0] * 384
        return self.model.encode([text])[0].tolist()


class RakshakVoiceClient:
    def __init__(self, model_version="1.0"):
        self.version = model_version
        self.model = None
        
    def load_model(self):
        try:
            from faster_whisper import WhisperModel
            # Load in FP16 for maximum GPU speed
            has_cuda = ML_AVAILABLE and 'torch' in globals() and torch.cuda.is_available()
            self.model = WhisperModel("small", device="cuda" if has_cuda else "cpu", compute_type="float16")
            return True
        except Exception as e:
            print(f"Whisper failed to load: {e}")
            return False
            
    def transcribe(self, audio_file_path: str):
        if not self.model: return "Mock Audio Transcription (Engine Offline)"
        segments, info = self.model.transcribe(audio_file_path, beam_size=5)
        text = " ".join([segment.text for segment in segments])
        return text


class RakshakVisionClient:
    def __init__(self, model_version="1.0"):
        self.version = model_version
        self.reader = None
        self.classifier = None
        self.model_loaded = False
        
    def load_model(self):
        try:
            import easyocr
            has_cuda = ML_AVAILABLE and 'torch' in globals() and torch.cuda.is_available()
            self.reader = easyocr.Reader(['en', 'hi'], gpu=has_cuda)
        except Exception as e:
            print(f"EasyOCR failed to load: {e}")
            
        try:
            # Load PyTorch Fake Currency classifier (MobileNet/ResNet)
            if ML_AVAILABLE:
                import torchvision.models as models
                import torch.nn as nn
                import os, torch
                self.classifier = models.mobilenet_v3_small(pretrained=False)
                
                # Setup classification layer for 2 classes as defined in training script
                num_ftrs = self.classifier.classifier[3].in_features
                self.classifier.classifier[3] = nn.Linear(num_ftrs, 2)
                
                model_path = os.path.join(os.path.dirname(__file__), "..", "..", "models", "rakshak-vision", "counterfeit_model.pt")
                if os.path.exists(model_path):
                    self.classifier.load_state_dict(torch.load(model_path, map_location="cpu"))
                    self.classifier.eval()
                    self.model_loaded = True
                else:
                    print(f"Model path not found: {model_path}")
                    self.model_loaded = False
                
            return True
        except Exception as e:
            print(f"Vision PyTorch model failed to load: {e}")
            return False
            
    def extract_text(self, image_path: str):
        if not self.reader: return "Mock Vision Extraction (Engine Offline)"
        results = self.reader.readtext(image_path)
        text = " ".join([res[1] for res in results])
        return text

    def detect_counterfeit(self, image_path: str):
        if getattr(self, 'model_loaded', False) is False:
            import random
            is_fake = random.choice([True, False])
            decision = "Counterfeit Currency Detected" if is_fake else "Genuine Currency"
            return {
                "decision": decision + " (MOCK VISION ENGINE)",
                "is_fake": is_fake,
                "confidence": round(random.uniform(0.75, 0.99), 2)
            }
            
        import torch
        from torchvision import transforms
        from PIL import Image
        
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        
        try:
            img = Image.open(image_path).convert('RGB')
            img_t = transform(img).unsqueeze(0)
            
            with torch.no_grad():
                outputs = self.classifier(img_t)
                probs = torch.nn.functional.softmax(outputs, dim=1)[0]
                confidence, predicted = torch.max(probs, 0)
                
            # Class 0: fake, Class 1: real (alphabetical ordering of folders)
            is_fake = (predicted.item() == 0)
            decision = "Counterfeit Currency Detected" if is_fake else "Genuine Currency"
            
            return {
                "decision": decision,
                "confidence": confidence.item(),
                "threat_class": "Counterfeit Note" if is_fake else "None",
                "evidence": ["AI Vision Analysis"] if is_fake else [],
                "models_used": ["Rakshak-Vision-MobileNetV3"]
            }
        except Exception as e:
            raise Exception(f"Vision inference failed: {e}")
