# Digital Rakshak: AI-Powered Cyber Threat Intelligence Platform

**Digital Rakshak** is a next-generation, hybrid AI-driven cyber-threat intelligence, classification, and prevention platform built to combat organized financial fraud and cybercrime in India. 

Moving beyond reactive complaint registration, Digital Rakshak leverages a massive **Multi-Agent AI Swarm**, **Graph Intelligence (Neo4j)**, and **Spatial Threat Mapping** to automatically identify organized crime syndicates, extract attack DNA, and provide actionable intelligence to Law Enforcement Agencies (LEAs), nodal officers, and citizens.

---

## 🚀 Unified Dual-Mode Architecture (Cloud vs. Offline)

Digital Rakshak features a state-of-the-art **Dual-Inference Engine** configured globally via the `DEFAULT_AI_MODE` environment variable. This allows the system to easily adapt to different deployment requirements:

### 1. Cloud-Native Mode (`groq` / `openrouter` / `azure`)
When set to cloud mode, the platform shifts its heavy analytical workloads to a **Cloud Runtime Provider Interface** (defaulting to **Groq's high-speed LPU Cloud**), bypassing all local hardware dependencies:
*   **The 11 AI Engines Swarm:** Dynamically routed in parallel to the cloud provider's **Llama 3.3 70B** model for deep reasoning, legal compliance, and behavioral analysis.
*   **RAIC Decision Core & Global Chat:** Routed to **Llama 3.1 8B**, leveraging a massive **128,000 token context window** to allow conversational analysis of entire case sheets without token limits.
*   **AI Copilot Transcription:** Sends voice evidence directly to the cloud **Whisper API** (`whisper-large-v3`).
*   **Zero-Hardware Footprint:** Runs instantly on Vercel Serverless Functions with zero memory/size limit crashes.

### 2. Local Native Mode (`auto` / `ollama`) — *Air-Gapped LEA Servers*
When set to local mode, the platform runs 100% self-contained on your own hardware with **zero external API calls or internet dependencies**, guaranteeing absolute data privacy for Law Enforcement:
*   **Rakshak Core (PyTorch):** The `ThreatAnalysisAgent` boots up our custom-trained **Rakshak Multi-Task Model** (a fine-tuned `distilbert-base-multilingual-cased` neural network) directly in CPU/GPU memory to perform multilingual Indian scam classification in under 15ms.
*   **Qwen2.5 Reasoning Engine:** Rather than treating Qwen as a basic local LLM, it serves as the central **Reasoning Engine** of the local stack—refining raw agent logs into highly professional, 2-sentence intelligence briefs for investigators.
*   **Local Audio Transcription:** The `WhisperAgent` runs a local **`faster-whisper`** instance.
*   **Local Screenshot OCR:** The `VisionAgent` runs a local **EasyOCR** English/Hindi reader.

---

## 🧠 The 11 Active Specialist Subagents (MAIF v10.0 Swarm)

The platform orchestrates 11 specialized subagents to analyze every case before the final fusion:

### Ingestion & Classification
1.  **ThreatAnalysisAgent (Rakshak-Text):** The primary classifier. Powered by the custom **Rakshak-Text (PyTorch)** model offline, it maps scams into 5 distinct threat classes (Safe, Banking Fraud, UPI Fraud, Courier Scam, Digital Arrest) and outputs a calibrated confidence score.
2.  **WhisperAgent (Voice Copilot):** The ears of the platform. Transcribes citizen voice recordings into text. In Cloud mode, it routes to Groq Whisper; offline, it falls back to local `faster-whisper`.
3.  **VisionAgent (Vision OCR):** The eyes of the platform. Extracts text, URLs, and banking details from uploaded screenshots.

### Deep Analytical Engines (Parallel execution)
4.  **BehaviourAgent (Rakshak-Behaviour):** Analyzes the attacker's psychological tactics (Fear, Urgency, Impersonation) to fingerprint the attack's behavioral DNA.
5.  **CampaignAgent (Rakshak-Link):** Uses local sentence embeddings (`BAAI/bge-small-en-v1.5`) to vector-search the database, clustering similar cases into unified, coordinated scam campaigns.
6.  **GeoAgent (Geo-Resolver):** Resolves geographic identifiers (cities, regions) mentioned in text to calculate spatial threat density.
7.  **TrustValidationAgent (ZTIVF):** Computes a multi-dimensional trust score based on reporter validation, checking for potential data-poisoning via evidence, user behavior, and correlations before trusting citizen input.

### Post-Processing & Persistence
8.  **TimelineAgent:** Builds a step-by-step chronological narrative of how the victim was targeted and scammed.
9.  **KnowledgeAgent:** Cross-references threat patterns with real-world Indian regulatory frameworks (RBI circulars, TRAI rules, IT Act).
10. **RecommendationAgent:** Formulates concrete actions for investigators (e.g. *"Freeze target Bank Account X"*, *"Block Phishing Domain Y"*).
11. **IntelligenceAgent:** Extracts all parsed entities (Phones, UPIs, IPs) and commits them as nodes and relationships in the **Neo4j Graph Database**.

---

## 👑 RAIC Decision Core & Confidence Fusion

Rather than simple output delivery, Digital Rakshak routes decisions through a mathematical fusion pipeline:

### 1. Multi-Dimensional Threat Scoring
The `RAICDecisionCore` merges individual agent outputs and breaks down the final score into 6 explainable dimensions:
*   **Threat Score:** The core classification probability.
*   **Behaviour Score:** The alignment with established fraud patterns.
*   **Campaign Score:** The duplicate/clustering index across multiple reports.
*   **Trust Score:** ZTIVF evaluation of the citizen and evidence integrity.
*   **Geo Score:** Geolocation density and hotspot proximity.
*   **Legal Score:** The severity of regulatory violations.

### 2. Intelligence Confidence Evolution
Confidence is a living metric. As new corroborating evidence arrives over time, the case confidence score evolves:
*   **Day 1 (Single Report):** Initial confidence starts at **~52%**.
*   **Bank Verification:** Rises to **~72%** once the bank confirms suspicious account transactions.
*   **Citizen Corroboration:** Rises to **~89%** when additional citizens report the same phone/UPI.
*   **Police Approval:** Solidifies to **~98%** upon investigator verification.
*   *Note: High-impact alerts (e.g., region-wide blocks or warning popups) are throttled until the confidence threshold matures, preventing false positives.*

### 3. Tiered Intelligence Promotion
To prevent database poisoning, threat data is promoted across three strict layers:
```
[ Submitted ] ──> [ Verified (Cyber Cell) ] ──> [ National Intelligence (NTIR) ] ──> [ Learning (Feedback Loop) ]
```

---

## 🛡️ Enterprise Feature Highlights

### 1. Conversational AI Form-Filling (Citizen Copilot)
Instead of forcing traumatized victims to fill out complex forms, they simply **talk naturally** to the AI Copilot. The background parser automatically transcribes the audio, extracts key fields (dates, amounts, bank names, scammer phone numbers), and populates the database fields in the background.

### 2. Counterfeit Currency Tracking & Local Warnings
When fake notes are reported:
*   The bank verifies the serial numbers and registers the incident.
*   The **GeoAgent** marks the region of discovery on the spatial map.
*   **PostGIS** automatically calculates the spread and pushes alert warnings to nearby merchant terminals and bank branches.

### 3. MITRE ATT&CK-Style Cyber Fraud DNA
Attack methodologies are categorized using an structured behavioral matrix:
```
Authority Impersonation ──> Urgency Creation ──> Credential Harvesting ──> Financial Extraction ──> Cleanup/Evasion
```

### 4. Enterprise AI Health & Telemetry Dashboard
Administrators have access to a real-time, glassmorphic hardware and software observability panel to monitor the orchestrator:
*   **Architecture Mode:** Instantly shows whether the system is running in **Cloud Mode (Groq)** or **Offline Mode (Qwen)**.
*   **Inference Engine Telemetry:** Monitors the active LLM provider, current models (e.g. Llama 3 70B / Qwen 2.5), and live API latency.
*   **Graph & Persistence Status:** Checks connectivity and latency to the Neo4j Intelligence Graph and PostgreSQL databases.
*   **Subagent Statuses:** Ensures all 11 subagents in the swarm are healthy and ready to process cases.

---

## 🗺️ Conceptual Platform Mapping

```
                    Citizens
                        │
                Should I Trust This?
                        │
               [ Zero Trust Gateway ]
                        │
                  [ RAIC Core ]
                        │
┌──────────────────────────────────────────┐
│          11 Intelligence Engines         │
│  Threat  •  Behaviour  •  Voice  •  Vision │
│   Geo   •  Campaign  • Knowledge • Policy │
│  Timeline • Recommendation • Trust Val.  │
└──────────────────────────────────────────┘
                        │
          [ Intelligence Correlation ]
                        │
          [ Qwen2.5 Reasoning Engine ]
                        │
            [ RAIC Decision Core ]
                        │
         [ Human Verification Layer ]
                        │
        [ Tiered Intelligence Promotion ]
         (EVR ──> ADR ──> TPR ──> NTIR)
                        │
┌──────────────────────────────────────────┐
│           Persistence Layer              │
│  Neo4j  •  PostGIS  •  pgvector  •  Redis  │
└──────────────────────────────────────────┘
                        │
┌──────────────────────────────────────────┐
│           Role-Based Dashboards          │
│   Citizen  •  Banker  •  Police  •  Admin │
└──────────────────────────────────────────┘
```

---

## 💻 Technology Stack

*   **Frontend:** Next.js 14 (App Router), React, Tailwind CSS, MapLibre GL, Framer Motion, Axios.
*   **Backend:** FastAPI, Python 3.12, SQLAlchemy 2.0 (Async), Asyncpg.
*   **Databases:** PostgreSQL (Relational & pgvector embeddings) and Neo4j (Graph data).
*   **AI Integration:** Groq Cloud LPU API (Llama 3.3 70B, Llama 3.1 8B, Whisper-large-v3), Local PyTorch (`xlm-roberta-base`), Local Ollama (`qwen2.5:7b`), Local EasyOCR.
*   **Deployment:** Vercel (Frontend & Serverless Backend).

---

## 🔧 Local Development Setup

### 1. Start the Databases (Docker)
```bash
docker-compose up -d
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
```
*   Create a `backend/.env` file containing your `DATABASE_URL`, `NEO4J_URI`, and `GROQ_API_KEY`.
*   Run database migrations and seed mockup threat cases:
```bash
# Migrations run programmatically on server start, but you can also run manually:
alembic upgrade head
python scripts/seed_diverse_cases.py
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
```
*   Create `frontend/.env.local` containing: `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/v1`
```bash
npm run dev
```
*   The application will be available at **`http://localhost:3000`**.

---

## 🐳 Docker Hub Quick Start (Pre-Built Images)
To run the platform without manually compiling PyTorch or setting up Node.js locally, you can pull our pre-built production images directly from Docker Hub:

### 1. Backend Service (Includes Python stack)
*   🔗 **[View Backend Image on Docker Hub](https://hub.docker.com/r/1065925/digital-rakshak-backend)**
```bash
docker pull 1065925/digital-rakshak-backend:latest
docker run -d -p 8000:8000 --env-file ./backend/.env --name dr-backend 1065925/digital-rakshak-backend:latest
```

### 2. Frontend Service (Includes Next.js build)
*   🔗 **[View Frontend Image on Docker Hub](https://hub.docker.com/r/1065925/digital-rakshak-frontend)**
```bash
docker pull 1065925/digital-rakshak-frontend:latest
docker run -d -p 3000:3000 --env-file ./frontend/.env.local --name dr-frontend 1065925/digital-rakshak-frontend:latest
```

---

## 🔒 Security & Contribution
This repository utilizes strict `.gitignore` rules to prevent credentials (`.env`, local database volumes, model weights) from being committed to public version control. If deploying, configure your cloud environment variables via Vercel or your hosting dashboard.

**Developed for a Safer Digital India.**
