from enum import Enum

class EventCatalog(str, Enum):
    """
    Formal Event Catalog for the Redis Streams Event Bus.
    Consumers subscribe to these specific event names to maintain strict bounded context boundaries.
    """
    # Case Management Events
    CASE_CREATED = "case.created"
    CASE_UPDATED = "case.updated"
    CASE_ESCALATED = "case.escalated"
    CASE_CLOSED = "case.closed"

    # Evidence & Intel Events
    EVIDENCE_INGESTED = "evidence.ingested"
    EVIDENCE_VERIFIED = "evidence.verified"
    THREAT_ANALYZED = "threat.analyzed"
    THREAT_VERIFIED = "threat.verified"

    # Campaign & Geospatial Events
    CAMPAIGN_DETECTED = "campaign.detected"
    CAMPAIGN_UPDATED = "campaign.updated"
    GEO_CLUSTER_UPDATED = "geo.cluster.updated"

    # Notification & Actions
    NOTIFICATION_REQUESTED = "notification.requested"
    BANK_FREEZE_REQUESTED = "action.bank_freeze.requested"

    # Intelligence Graph Updates (Neo4j / PostGIS synchronization triggers)
    GRAPH_ENTITY_MERGED = "graph.entity.merged"
    VECTOR_EMBEDDING_GENERATED = "vector.embedding.generated"
