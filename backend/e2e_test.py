import asyncio
import os
import sys

# Add backend to path explicitly to be safe
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

async def test_e2e():
    print("=== STARTING END-TO-END VERIFICATION ===\n")
    
    # 1. Test RakshakVisionClient (Counterfeit Model)
    print("1. Testing RakshakVisionClient...")
    try:
        from infrastructure.ai.ml_client import RakshakVisionClient
        vision = RakshakVisionClient()
        vision.load_model()
        
        # Test detection
        print("  - Running detect_counterfeit()...")
        res = vision.detect_counterfeit("dummy.jpg")
        print(f"  [SUCCESS] Vision returned: {res['decision']} with {res['confidence']*100:.1f}% confidence")
    except Exception as e:
        print(f"  [FAIL] VisionClient failed: {e}")
        
    print("\n2. Testing RAIC Decision Core & 6-Dimension Score...")
    try:
        from domain.agents.router import RAICDecisionCore
        core = RAICDecisionCore()
        
        # Mock agent payloads
        payloads = [
            {
                "agent": "ThreatAnalysisAgent",
                "threat_class": "Financial Fraud",
                "confidence": 0.95,
                "reasoning": ["Matches known fraud patterns"]
            },
            {
                "agent": "BehaviourAgent",
                "evidence": ["T1566: Phishing (Impersonation)", "T1484: Domain Policy (Urgency/Pressure)"],
                "confidence": 0.90
            },
            {
                "agent": "TrustValidationAgent",
                "entities": {"identity_score": 0.2, "evidence_score": 0.9},
                "confidence": 0.8
            }
        ]
        
        print("  - Executing fusion...")
        # Since use_qwen_refinement uses Groq/Ollama, we'll set it to False to just test the local core logic
        res = await core.execute_fusion(payloads, use_qwen_refinement=False)
        print(f"  [SUCCESS] Fusion generated decision: {res['decision'][:60]}...")
        print(f"  [SUCCESS] Fused Confidence: {res['confidence']*100:.1f}%")
        
        print("  - Checking 6-Dimension Score...")
        if 'six_dim_score' in res:
            print(f"  [SUCCESS] 6-Axis Score found: {res['six_dim_score']}")
        else:
            print("  [FAIL] 6-Axis Score MISSING!")
    except Exception as e:
        print(f"  [FAIL] Router failed: {e}")

    print("\n3. Testing Cases process_case_background intercept...")
    print("  - To test this without Neo4j/Postgres, we verify the code logic.")
    # Check if 'report_type' exists in the signature
    try:
        import inspect
        from api.v1.cases import process_case_background
        sig = inspect.signature(process_case_background)
        if 'report_type' in sig.parameters:
            print(f"  [SUCCESS] process_case_background accepts 'report_type'")
        else:
            print("  [FAIL] process_case_background missing 'report_type'")
    except Exception as e:
        print(f"  [FAIL] cases.py inspection failed: {e}")

    print("\n=== E2E VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_e2e())
