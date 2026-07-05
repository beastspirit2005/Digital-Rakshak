from abc import ABC, abstractmethod
from typing import Any, Dict, List
import time

class AgentLifecycleError(Exception):
    pass

class BaseAgent(ABC):
    """
    Abstract Base Class for all AI Agents in the RAIC Platform.
    Enforces a strict lifecycle to ensure consistency, audibility, and 
    easy integration of future agents.
    """
    
    def __init__(self, agent_name: str, version: str):
        self.agent_name = agent_name
        self.version = version
        self.initialize()

    @abstractmethod
    def initialize(self) -> None:
        """Step 1: Load agent config, prompt templates, and routing weights."""
        pass

    @abstractmethod
    def validate_input(self, payload: Dict[str, Any]) -> bool:
        """Step 2: Ensure the payload meets the agent's expected schema."""
        pass

    @abstractmethod
    async def retrieve_context(self, case_id: str) -> Dict[str, Any]:
        """Step 3: Fetch necessary data from the Intelligence Graph."""
        pass

    @abstractmethod
    async def inference(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Step 4: Call the primary model (Gemini) or fallback (Ollama)."""
        pass

    @abstractmethod
    def calculate_confidence(self, raw_score: float) -> float:
        """Step 5: Apply mathematical bounds (clamping) to the raw score."""
        pass
        
    def generate_decision_object(
        self, 
        engine: str,
        engine_version: str,
        model_version: str,
        confidence: float, 
        entities: List[Any],
        evidence: List[Any],
        reasoning: List[str],
        recommendation: List[str],
        prompt_version: str,
        inference_time_ms: int
    ) -> Dict[str, Any]:
        """Step 6: Output the standardized Explainability Object."""
        return {
            "agent": self.agent_name,
            "engine": engine,
            "engine_version": engine_version,
            "model_version": model_version,
            "prompt_version": prompt_version,
            "confidence": confidence,
            "execution_time_ms": inference_time_ms,
            "evidence_count": len(evidence),
            "entities": entities,
            "evidence": evidence,
            "reasoning": reasoning,
            "recommendation": recommendation
        }

    @abstractmethod
    async def publish_event(self, event_name: str, decision_object: Dict[str, Any]) -> None:
        """Step 7: Push the outcome to the Redis Stream Event Bus."""
        pass

    async def execute(self, payload: Dict[str, Any], case_id: str) -> Dict[str, Any]:
        """
        The Template Method that orchestrates the strict agent lifecycle.
        """
        start_time = time.time()
        
        if not self.validate_input(payload):
            raise AgentLifecycleError(f"{self.agent_name}: Invalid input payload.")
            
        context = await self.retrieve_context(case_id)
        
        # Extract ai_mode from payload and inject into context so inference() can use it
        if "ai_mode" in payload:
            context["ai_mode"] = payload["ai_mode"]
        
        # Build prompt from text only (not the entire payload dict)
        prompt = payload.get("text", str(payload))
        
        inference_result = await self.inference(prompt, context)
        raw_score = inference_result.get("score", 0.0)
        
        confidence = self.calculate_confidence(raw_score)
        
        end_time = time.time()
        inference_time_ms = int((end_time - start_time) * 1000)
        
        decision_obj = self.generate_decision_object(
            engine=inference_result.get("engine", "Unknown"),
            engine_version=inference_result.get("engine_version", "1.0"),
            model_version=inference_result.get("model_version", "1.0"),
            confidence=confidence,
            entities=inference_result.get("entities", []),
            evidence=inference_result.get("evidence", []),
            reasoning=inference_result.get("reasoning", []),
            recommendation=inference_result.get("recommendation", []),
            prompt_version=inference_result.get("prompt_version", "n/a"),
            inference_time_ms=inference_time_ms
        )
        
        # Preserve estimated coordinates from inference for spatial mapping
        if inference_result.get("estimated_latitude") is not None:
            decision_obj["estimated_latitude"] = inference_result["estimated_latitude"]
        if inference_result.get("estimated_longitude") is not None:
            decision_obj["estimated_longitude"] = inference_result["estimated_longitude"]
        
        # Preserve threat_class from ThreatAnalysisAgent for RAIC Decision Core fusion
        if inference_result.get("threat_class") is not None:
            decision_obj["threat_class"] = inference_result["threat_class"]
        
        # Preserve the raw score for spatial heatmap weighting
        decision_obj["score"] = raw_score
        
        await self.publish_event(f"threat.analyzed.{self.agent_name.lower()}", decision_obj)
        
        return decision_obj
