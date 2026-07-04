"""
Digital Rakshak - Master Blueprint Verification Script
Senior Dev Executive QA Pass
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import requests
import json
import importlib
import os

BASE = "http://127.0.0.1:8000/api/v1"
PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"
results = {"pass": 0, "fail": 0, "warn": 0}

def check(name, condition, detail=""):
    global results
    if condition:
        results["pass"] += 1
        print(f"  {PASS} {name} {detail}")
    else:
        results["fail"] += 1
        print(f"  {FAIL} {name} {detail}")

def warn(name, detail=""):
    global results
    results["warn"] += 1
    print(f"  {WARN} {name} {detail}")

# ========================================
# SECTION 1: INFRASTRUCTURE
# ========================================
print("\n" + "="*60)
print("SECTION 1: INFRASTRUCTURE HEALTH")
print("="*60)

try:
    r = requests.get(f"{BASE}/health", timeout=5)
    data = r.json()
    check("Health endpoint", r.status_code == 200)
    check("PostgreSQL", data["services"]["postgres"]["status"] == "up")
    check("Redis", data["services"]["redis"]["status"] == "up")
    check("Neo4j", data["services"]["neo4j"]["status"] == "up")
except Exception as e:
    check("Health endpoint", False, str(e))

# ========================================
# SECTION 2: AUTHENTICATION
# ========================================
print("\n" + "="*60)
print("SECTION 2: AUTHENTICATION & RBAC")
print("="*60)

token = None
try:
    r = requests.post(f"{BASE}/auth/login-password", json={"email": "harshit2500sharma@gmail.com", "password": "Admin@123"}, timeout=5)
    check("Admin login", r.status_code == 200, f"(status={r.status_code})")
    if r.status_code == 200:
        token = r.json()["access_token"]
        user = r.json()["user"]
        check("Admin role", user["role"] == "admin", f"(role={user['role']})")
except Exception as e:
    check("Admin login", False, str(e))

headers = {"Authorization": f"Bearer {token}"} if token else {}

# ========================================
# SECTION 3: CASE SUBMISSION PIPELINE
# ========================================
print("\n" + "="*60)
print("SECTION 3: CASE SUBMISSION PIPELINE")
print("="*60)

try:
    r = requests.get(f"{BASE}/cases/", headers=headers, timeout=5)
    check("GET /cases/", r.status_code == 200, f"(count={len(r.json().get('cases', []))})")
except Exception as e:
    check("GET /cases/", False, str(e))

try:
    r = requests.get(f"{BASE}/cases/my", headers=headers, timeout=5)
    check("GET /cases/my", r.status_code == 200)
except Exception as e:
    check("GET /cases/my", False, str(e))

try:
    r = requests.get(f"{BASE}/cases/spatial", headers=headers, timeout=5)
    data = r.json()
    check("GET /cases/spatial (GeoJSON)", r.status_code == 200 and data.get("type") == "FeatureCollection",
          f"(features={len(data.get('features', []))})")
except Exception as e:
    check("GET /cases/spatial", False, str(e))

try:
    r = requests.get(f"{BASE}/cases/clusters", headers=headers, timeout=5)
    data = r.json()
    check("GET /cases/clusters (Neo4j web)", r.status_code == 200,
          f"(cluster_lines={len(data.get('features', []))})")
except Exception as e:
    check("GET /cases/clusters", False, str(e))

# ========================================
# SECTION 4: GRAPH EXPLORER API
# ========================================
print("\n" + "="*60)
print("SECTION 4: GRAPH EXPLORER API")
print("="*60)

try:
    r = requests.get(f"{BASE}/graph/network", headers=headers, timeout=10)
    data = r.json()
    n_count = len(data.get('nodes', []))
    l_count = len(data.get('links', []))
    check("GET /graph/network", r.status_code == 200,
          f"(nodes={n_count}, links={l_count})") 
except Exception as e:
    check("GET /graph/network", False, str(e))

# ========================================
# SECTION 5: BACKEND AGENT IMPORTS
# ========================================
print("\n" + "="*60)
print("SECTION 5: BACKEND AI AGENT IMPORTS")
print("="*60)

agents_to_check = [
    ("domain.agents.base", "BaseAgent"),
    ("domain.agents.threat_agent", "ThreatAnalysisAgent"),
    ("domain.agents.vision_agent", "VisionAgent"),
    ("domain.agents.whisper_agent", "WhisperAgent"),
    ("domain.agents.cluster_agent", "ClusterAgent"),
    ("domain.agents.fusion_agent", "FusionAgent"),
    ("domain.agents.policy_agent", "PolicyAgent"),
    ("domain.agents.behaviour_agent", "BehaviourAgent"),
    ("domain.agents.campaign_agent", "CampaignAgent"),
    ("domain.agents.geo_agent", "GeoAgent"),
    ("domain.agents.knowledge_agent", "KnowledgeAgent"),
    ("domain.agents.recommendation_agent", "RecommendationAgent"),
    ("domain.agents.timeline_agent", "TimelineAgent"),
    ("domain.agents.router", "AIRouter"),
]

for module_path, class_name in agents_to_check:
    try:
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        check(f"{class_name}", True, f"(from {module_path})")
    except Exception as e:
        check(f"{class_name}", False, f"IMPORT ERROR: {e}")

# ========================================
# SECTION 6: INFRASTRUCTURE MODULES
# ========================================
print("\n" + "="*60)
print("SECTION 6: INFRASTRUCTURE MODULES")
print("="*60)

infra_modules = [
    ("infrastructure.security.encryption", "PIIEncryptionService"),
    ("infrastructure.event_bus.redis_streams", "EventBus"),
    ("infrastructure.graph.neo4j_client", "IntelligenceGraph"),
    ("infrastructure.osint.scanner", "OSINTScanner"),
    ("domain.agents.router", "AIRouter"),
]

for module_path, name in infra_modules:
    try:
        mod = importlib.import_module(module_path)
        obj = getattr(mod, name)
        check(f"{name}", True, f"(from {module_path})")
    except Exception as e:
        check(f"{name}", False, f"IMPORT ERROR: {e}")

# ========================================
# SECTION 7: DATABASE SCHEMA
# ========================================
print("\n" + "="*60)
print("SECTION 7: DATABASE SCHEMA VERIFICATION")
print("="*60)

import subprocess
col_check = subprocess.run(
    ["docker", "exec", "dr-postgres", "psql", "-U", "rakshak_admin", "-d", "digital_rakshak", "-t", "-c",
     "SELECT column_name FROM information_schema.columns WHERE table_name = 'cases' ORDER BY ordinal_position;"],
    capture_output=True, text=True
)
columns = [c.strip() for c in col_check.stdout.strip().split("\n") if c.strip()]

required_cols = ["id", "case_number", "scam_text", "latitude", "longitude", "threat_confidence_score", 
                 "ai_decision", "attack_dna", "timeline_events", "semantic_embedding", "geom"]
for col in required_cols:
    check(f"Column: cases.{col}", col in columns)

# Check extensions
ext_check = subprocess.run(
    ["docker", "exec", "dr-postgres", "psql", "-U", "rakshak_admin", "-d", "digital_rakshak", "-t", "-c",
     "SELECT extname FROM pg_extension;"],
    capture_output=True, text=True
)
extensions = ext_check.stdout.strip()
check("PostGIS extension", "postgis" in extensions)
check("pgvector extension", "vector" in extensions)

# ========================================
# SECTION 8: FRONTEND FILES
# ========================================
print("\n" + "="*60)
print("SECTION 8: FRONTEND PAGE/COMPONENT FILES")
print("="*60)

frontend_base = r"c:\Users\Lenovo\Desktop\DigitalRakshak\frontend\src"
required_pages = [
    ("app/(dashboard)/prevention/page.tsx", "Prevention Suite"),
    ("app/(dashboard)/copilot/page.tsx", "AI Co-Pilot"),
    ("app/(dashboard)/workbench/graph/page.tsx", "Graph Explorer"),
    ("app/(dashboard)/citizen/page.tsx", "Citizen Dashboard"),
    ("app/(dashboard)/workbench/map/page.tsx", "Spatial Map"),
    ("app/(dashboard)/report/page.tsx", "Report Page"),
    ("components/case-timeline.tsx", "Case Timeline Component"),
    ("components/graph/network-visualizer.tsx", "Network Visualizer (Cytoscape)"),
    ("components/map/spatial-map.tsx", "Spatial Map Component"),
    ("components/protected-route.tsx", "Protected Route (RBAC)"),
]

for path, name in required_pages:
    full = os.path.join(frontend_base, path)
    check(f"{name}", os.path.exists(full), f"({path})")

# ========================================
# SECTION 9: SECURITY FEATURES
# ========================================
print("\n" + "="*60)
print("SECTION 9: SECURITY & CHAIN OF CUSTODY")
print("="*60)

# Test encryption service
try:
    from infrastructure.security.encryption import PIIEncryptionService
    enc = PIIEncryptionService()
    test_data = "Victim: Rahul Sharma, Phone: +919876543210"
    encrypted = enc.encrypt(test_data)
    decrypted = enc.decrypt(encrypted)
    check("AES-256 Encrypt/Decrypt", decrypted == test_data, "(round-trip verified)")
    check("Ciphertext != plaintext", encrypted != test_data)
except Exception as e:
    check("AES-256 Encryption", False, str(e))

# Test SHA-256 in cases.py
import ast
cases_path = r"c:\Users\Lenovo\Desktop\DigitalRakshak\backend\api\v1\cases.py"
with open(cases_path, 'r') as f:
    cases_code = f.read()
check("SHA-256 hashing in cases.py", "sha256" in cases_code.lower())

# Test Redis event bus
try:
    from infrastructure.event_bus.redis_streams import event_bus
    check("Redis EventBus import", True)
except Exception as e:
    check("Redis EventBus", False, str(e))

# ========================================
# SECTION 10: FUSION AGENT INTEGRATION
# ========================================
print("\n" + "="*60)
print("SECTION 10: FUSION AGENT INTEGRATION CHECK")
print("="*60)

fusion_path = r"c:\Users\Lenovo\Desktop\DigitalRakshak\backend\domain\agents\fusion_agent.py"
with open(fusion_path, 'r') as f:
    fusion_code = f.read()

check("Fusion imports BehaviourAgent", "BehaviourAgent" in fusion_code)
check("Fusion imports KnowledgeAgent", "KnowledgeAgent" in fusion_code)
check("Fusion imports TimelineAgent", "TimelineAgent" in fusion_code)
check("Fusion imports RecommendationAgent", "RecommendationAgent" in fusion_code)
check("Fusion runs agents in parallel", "asyncio.gather" in fusion_code)
check("Fusion accepts raw_text param", "raw_text" in fusion_code)

# ========================================
# FINAL REPORT
# ========================================
print("\n" + "="*60)
print(f"FINAL REPORT")
print("="*60)
total = results["pass"] + results["fail"] + results["warn"]
print(f"\n  Total checks: {total}")
print(f"  {PASS} Passed: {results['pass']}")
print(f"  {FAIL} Failed: {results['fail']}")
print(f"  {WARN} Warnings: {results['warn']}")
pct = (results['pass'] / total * 100) if total > 0 else 0
print(f"\n  Score: {pct:.1f}% ({results['pass']}/{total})")
print()
