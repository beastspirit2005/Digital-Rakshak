"""
RAICFactory — Dependency Injection Container for the RAIC Pipeline.

Wires the full chain:
  Runtime → Engine → Capability → Agent → Registry

Usage in cases.py:
    from raic.factory import RAICFactory
    registry, planner, engine = RAICFactory.build(ai_mode=settings.DEFAULT_AI_MODE)
"""

import logging
from raic.agent_registry import AgentRegistry
from raic.planner import ExecutionPlanner
from raic.execution_engine import ExecutionEngine
from shared.contexts.investigation import InvestigationContext, EvidenceContext

logger = logging.getLogger(__name__)


class RAICFactory:

    @staticmethod
    def build(ai_mode: str = "groq") -> tuple[AgentRegistry, ExecutionPlanner, ExecutionEngine]:
        """
        Constructs and wires the full RAIC dependency tree.
        Returns (registry, planner, engine) ready for use by the Orchestrator.
        """
        from rie.runtime_registry import RuntimeRegistry
        from rie.runtimes.reasoning_runtime import RakshakReasoningRuntime
        from rie.runtimes.ner_runtime import RakshakNERRuntime
        from rie.runtimes.behaviour_runtime import RakshakBehaviourRuntime
        from rie.runtimes.embedding_runtime import RakshakEmbeddingRuntime
        from rie.runtimes.threat_runtime import RakshakThreatRuntime

        # ── 1. Build Runtime Registry ────────────────────────────────────────
        runtime_registry = RuntimeRegistry()
        runtime_registry.register("reasoning_runtime",  RakshakReasoningRuntime(ai_mode=ai_mode))
        runtime_registry.register("ner_runtime",        RakshakNERRuntime())
        runtime_registry.register("behaviour_runtime",  RakshakBehaviourRuntime(ai_mode=ai_mode))
        runtime_registry.register("embedding_runtime",  RakshakEmbeddingRuntime())
        runtime_registry.register("threat_runtime",     RakshakThreatRuntime())
        logger.info("RIE RuntimeRegistry built with 5 runtimes.")

        # ── 2. Build Intelligence Engines ────────────────────────────────────
        from rie.engines.threat_intelligence_engine     import ThreatIntelligenceEngine
        from rie.engines.behaviour_intelligence_engine  import BehaviourIntelligenceEngine
        from rie.engines.campaign_intelligence_engine   import CampaignIntelligenceEngine
        from rie.engines.knowledge_intelligence_engine  import KnowledgeIntelligenceEngine
        from rie.engines.evidence_intelligence_engine   import EvidenceIntelligenceEngine

        threat_engine     = ThreatIntelligenceEngine(runtime_registry)
        behaviour_engine  = BehaviourIntelligenceEngine(runtime_registry)
        campaign_engine   = CampaignIntelligenceEngine(runtime_registry)
        knowledge_engine  = KnowledgeIntelligenceEngine(runtime_registry)
        evidence_engine   = EvidenceIntelligenceEngine(runtime_registry)
        logger.info("RIE Intelligence Engines built.")

        # ── 3. Build Capabilities ────────────────────────────────────────────
        from raic.capabilities.threat_capability    import ThreatCapability
        from raic.capabilities.behaviour_capability import BehaviourCapability
        from raic.capabilities.campaign_capability  import CampaignCapability
        from raic.capabilities.vision_capability    import VisionCapability
        from raic.capabilities.voice_capability     import VoiceCapability

        threat_cap    = ThreatCapability(threat_engine)
        behaviour_cap = BehaviourCapability(behaviour_engine)
        campaign_cap  = CampaignCapability(campaign_engine)
        vision_cap    = VisionCapability(evidence_engine)
        voice_cap     = VoiceCapability(knowledge_engine)
        logger.info("RAIC Capabilities built.")

        # ── 4. Build Agents ──────────────────────────────────────────────────
        from raic.agents.threat_agent    import ThreatAgent
        from raic.agents.behaviour_agent import BehaviourAgent
        from raic.agents.campaign_agent  import CampaignAgent
        from raic.agents.vision_agent    import VisionAgent
        from raic.agents.voice_agent     import VoiceAgent

        threat_agent    = ThreatAgent(threat_cap)
        behaviour_agent = BehaviourAgent(behaviour_cap)
        campaign_agent  = CampaignAgent(campaign_cap)
        vision_agent    = VisionAgent(vision_cap)
        voice_agent     = VoiceAgent(voice_cap)
        logger.info("RAIC Agents built.")

        # ── 5. Build Synthetic Agents for Decision Core stages ───────────────
        #    The Planner requests these agents by name. We create lightweight
        #    pass-through wrappers for the stages the Decision Core handles
        #    internally (consensus, decision, explainability) so the engine
        #    doesn't log a ValueError and skip them.
        from raic.agents._synthetic import NoOpAgent
        evidence_agent      = NoOpAgent("evidence_agent")
        knowledge_agent     = NoOpAgent("knowledge_agent")
        consensus_agent     = NoOpAgent("consensus_agent")
        decision_agent      = NoOpAgent("decision_agent")
        explainability_agent = NoOpAgent("explainability_agent")

        # ── 6. Register all Agents ───────────────────────────────────────────
        registry = AgentRegistry()
        # Classification stage (parallel)
        registry.register("threat_agent",    threat_agent)
        registry.register("behaviour_agent", behaviour_agent)
        registry.register("campaign_agent",  campaign_agent)
        registry.register("vision_agent",    vision_agent)
        registry.register("voice_agent",     voice_agent)
        # Pipeline stage stubs
        registry.register("evidence_agent",      evidence_agent)
        registry.register("knowledge_agent",     knowledge_agent)
        registry.register("consensus_agent",     consensus_agent)
        registry.register("decision_agent",      decision_agent)
        registry.register("explainability_agent", explainability_agent)
        logger.info("AgentRegistry populated with 10 agents.")

        # ── 7. Build Planner and Engine ──────────────────────────────────────
        planner = ExecutionPlanner(registry)
        engine  = ExecutionEngine(registry)

        return registry, planner, engine

    @staticmethod
    def build_investigation_context(case) -> InvestigationContext:
        """
        Maps a DB Case object to an InvestigationContext for the RAIC pipeline.
        """
        from shared.contexts.investigation import RuntimeContext

        evidence = []
        if case.scam_text:
            evidence.append(EvidenceContext(
                evidence_id=str(case.id),
                content_type="text/plain",
                raw_data=case.scam_text,
                metadata={
                    "case_number": case.case_number,
                    "report_type": getattr(case, "report_type", "cybercrime"),
                    "city": getattr(case, "city", ""),
                    "state": getattr(case, "state", ""),
                }
            ))

        return InvestigationContext(
            case_id=str(case.id),
            evidence=evidence,
            runtime=RuntimeContext(
                priority="high",
                timeout_seconds=45,
                strict_mode=False
            )
        )
