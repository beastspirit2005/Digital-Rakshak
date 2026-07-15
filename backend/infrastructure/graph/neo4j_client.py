from neo4j import AsyncGraphDatabase
import logging
import re
from core.config import settings

logger = logging.getLogger(__name__)

import threading

class IntelligenceGraph:
    """
    Client for Neo4j. Acts as the Intelligence Graph Layer storing entities
    like PhoneNumbers, BankAccounts, IPAddresses and their relationships
    to Cases to detect coordinated campaigns.
    """
    _driver = None
    _lock = threading.Lock()

    def __init__(self):
        if IntelligenceGraph._driver is None:
            with IntelligenceGraph._lock:
                if IntelligenceGraph._driver is None:
                    IntelligenceGraph._driver = AsyncGraphDatabase.driver(
                        settings.NEO4J_URI,
                        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                        max_connection_lifetime=3600,
                        max_connection_pool_size=50
                    )
        self.driver = IntelligenceGraph._driver

    async def close(self):
        # We don't close the driver on individual instances anymore because it's shared.
        # It will be closed on app shutdown.
        pass
        
    @classmethod
    async def close_driver(cls):
        if cls._driver is not None:
            await cls._driver.close()
            cls._driver = None

    @staticmethod
    def _sanitize_label(label: str, default: str = "Entity") -> str:
        if not label or not isinstance(label, str) or not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', label):
            return default
        return label

    @staticmethod
    def _sanitize_relation(relation: str, default: str = "INVOLVES") -> str:
        if not relation or not isinstance(relation, str) or not re.match(r'^[A-Z][A-Z0-9_]*$', relation):
            return default
        return relation

    async def add_case_entity_link(self, case_id: str, entity_type: str, entity_value: str, relation: str = "INVOLVES"):
        """
        Links a Case node to an Entity node (e.g. PhoneNumber).
        Creates nodes if they don't exist.
        """
        safe_type = self._sanitize_label(entity_type)
        safe_relation = self._sanitize_relation(relation)
        query = f"""
        MERGE (c:Case {{id: $case_id}})
        MERGE (e:{safe_type} {{value: $entity_value}})
        MERGE (c)-[:{safe_relation}]->(e)
        RETURN c, e
        """
        async with self.driver.session() as session:
            try:
                await session.run(query, case_id=case_id, entity_value=entity_value)
                logger.info(f"Created link from Case {case_id} to {safe_type} {entity_value}")
            except Exception as e:
                logger.error(f"Neo4j Error creating link: {e}")

    async def get_related_cases(self, entity_type: str, entity_value: str):
        """
        Finds all cases connected to a specific entity. Used for campaign correlation.
        """
        safe_type = self._sanitize_label(entity_type)
        query = f"""
        MATCH (c:Case)-[]->(e:{safe_type} {{value: $entity_value}})
        RETURN c.id as case_id
        """
        async with self.driver.session() as session:
            try:
                result = await session.run(query, entity_value=entity_value)
                records = await result.data()
                return [r["case_id"] for r in records]
            except Exception as e:
                logger.error(f"Neo4j Error querying related cases: {e}")
                return []

    async def get_entities_for_case(self, case_id: str):
        """
        Finds all entities connected to a specific case.
        Returns a list of entity values.
        """
        query = """
        MATCH (c:Case {id: $case_id})-[]->(e)
        RETURN e.value as entity_value
        """
        async with self.driver.session() as session:
            try:
                result = await session.run(query, case_id=case_id)
                records = await result.data()
                return [r["entity_value"] for r in records]
            except Exception as e:
                logger.error(f"Neo4j Error querying entities for case {case_id}: {e}")
                return []

    async def get_connected_clusters(self):
        """
        Finds all cases that share the same PhoneNumber, UPI_ID, or URL.
        Returns clusters of case IDs and the entity connecting them.
        """
        query = """
        MATCH (c:Case)-[]->(e)
        WHERE e:PhoneNumber OR e:UPI_ID OR e:URL OR e:BankAccount
        WITH e, collect(c.id) as case_ids
        WHERE size(case_ids) > 1
        RETURN labels(e)[0] as entity_type, e.value as entity_value, case_ids
        """
        async with self.driver.session() as session:
            try:
                result = await session.run(query)
                records = await result.data()
                return records
            except Exception as e:
                logger.error(f"Neo4j Error querying connected clusters: {e}")
                return []

    async def add_osint_entity(self, entity_type: str, entity_value: str, source: str, threat_type: str):
        """
        Marks an entity as a known threat from an OSINT source.
        Adds the :ThreatIntel label to it.
        """
        safe_type = self._sanitize_label(entity_type)
        query = f"""
        MERGE (e:{safe_type} {{value: $entity_value}})
        SET e:ThreatIntel
        SET e.osint_source = $source
        SET e.threat_type = $threat_type
        RETURN e
        """
        async with self.driver.session() as session:
            try:
                await session.run(query, entity_value=entity_value, source=source, threat_type=threat_type)
                logger.info(f"OSINT ThreatIntel added: {safe_type} {entity_value} ({threat_type})")
            except Exception as e:
                logger.error(f"Neo4j Error adding OSINT entity: {e}")

    async def get_osint_flags_for_entities(self, entities: list) -> list:
        """
        Given a list of entity values (e.g., phone numbers), checks if any are marked as :ThreatIntel.
        Returns a list of OSINT flags.
        """
        if not entities:
            return []
            
        query = """
        MATCH (e:ThreatIntel)
        WHERE e.value IN $entities
        RETURN labels(e) as labels, e.value as value, e.osint_source as source, e.threat_type as threat_type
        """
        async with self.driver.session() as session:
            try:
                result = await session.run(query, entities=entities)
                records = await result.data()
                return records
            except Exception as e:
                logger.error(f"Neo4j Error checking OSINT flags: {e}")
                return []
