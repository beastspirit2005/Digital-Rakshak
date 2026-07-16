from typing import Any, Dict
from backend.shared.contracts.capability import ICapability
from backend.shared.contracts.runtime import IEmbeddingRuntime, INERRuntime
import asyncio

class CampaignCapability(ICapability):
    def __init__(self, embedding_runtime: IEmbeddingRuntime, ner_runtime: INERRuntime):
        self._embedding_runtime = embedding_runtime
        self._ner_runtime = ner_runtime

    async def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        text = payload.get("text")
        if not text:
            raise ValueError("CampaignCapability requires 'text' in payload.")
            
        # Run runtimes concurrently
        emb_task = self._embedding_runtime.infer({"text": text})
        ner_task = self._ner_runtime.infer({"text": text})
        
        emb_result, ner_result = await asyncio.gather(emb_task, ner_task)
        
        # Mock similarity check (would connect to Neo4j)
        similarity_found = True
        confidence = 0.95 if similarity_found else 0.20
        
        return {
            "embeddings": emb_result["embeddings"],
            "entities": ner_result["entities"],
            "confidence": confidence,
            "execution_time_ms": emb_result["execution_time_ms"] + ner_result["execution_time_ms"],
            "metadata": {
                "embedding_engine": emb_result["engine"],
                "ner_engine": ner_result["engine"]
            }
        }
