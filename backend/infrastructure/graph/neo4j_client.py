from neo4j import AsyncGraphDatabase
import logging
import re
import asyncio
import threading
from core.config import settings

logger = logging.getLogger(__name__)

class IntelligenceGraph:
    """
    Client for Neo4j. Acts as the Intelligence Graph Layer storing entities
    like PhoneNumbers, BankAccounts, IPAddresses and their relationships
    to Cases to detect coordinated campaigns.
    """
    _driver = None
    _loop = None
    _lock = threading.Lock()

    def __init__(self):
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

        if IntelligenceGraph._driver is None or (IntelligenceGraph._loop is not None and IntelligenceGraph._loop != loop):
            with IntelligenceGraph._lock:
                if IntelligenceGraph._driver is None or (IntelligenceGraph._loop is not None and IntelligenceGraph._loop != loop):
                    IntelligenceGraph._driver = AsyncGraphDatabase.driver(
                        settings.NEO4J_URI,
                        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                        max_connection_lifetime=3600,
                        max_connection_pool_size=50
                    )
                    IntelligenceGraph._loop = loop
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
                raise

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

    # -----------------------------------------------------------------------
    # Transaction Fraud Intelligence Graph Layer
    # -----------------------------------------------------------------------
    async def record_transaction_graph(
        self,
        account_id: str,
        transaction_id: str,
        beneficiary_id: str,
        amount: Optional[float] = None,
        device_id: Optional[str] = None,
        channel: Optional[str] = None,
        location_name: Optional[str] = None,
        timestamp: Optional[Any] = None,
        **kwargs
    ):
        """
        Ingests a financial transaction and creates (:Account)-[:MADE]->(:Transaction)-[:SENT_TO]->(:Beneficiary).
        Also links (:Account)-[:USES]->(:Device) and (:Account)-[:LOCATED_AT]->(:Location).
        """
        query = """
        MERGE (a:Account {id: $account_id})
        MERGE (t:Transaction {id: $transaction_id})
        ON CREATE SET t.amount = $amount, t.channel = $channel
        ON MATCH SET t.amount = $amount, t.channel = $channel
        MERGE (b:Beneficiary {id: $beneficiary_id})
        MERGE (a)-[:MADE]->(t)
        MERGE (t)-[:SENT_TO]->(b)
        """
        params = {
            "account_id": str(account_id),
            "transaction_id": str(transaction_id),
            "beneficiary_id": str(beneficiary_id).lower().strip(),
            "amount": float(amount) if amount is not None else 0.0,
            "channel": str(channel) if channel is not None else "UPI"
        }

        if device_id:
            query += """
            MERGE (d:Device {id: $device_id})
            MERGE (a)-[:USES]->(d)
            """
            params["device_id"] = str(device_id)

        if location_name:
            query += """
            MERGE (l:Location {name: $location_name})
            MERGE (a)-[:LOCATED_AT]->(l)
            """
            params["location_name"] = str(location_name)

        async with self.driver.session() as session:
            try:
                await session.run(query, **params)
                logger.info(f"Transaction graph recorded: {transaction_id} (Account: {account_id} -> Beneficiary: {beneficiary_id})")
            except Exception as e:
                logger.error(f"Neo4j Error recording transaction graph: {e}")

    async def get_transaction_fraud_ring(
        self,
        account_id: str,
        beneficiary_id: str,
        device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detects if the transaction connects into a coordinated fraud ring:
        1. Device used by multiple accounts
        2. Beneficiary receiving from multiple accounts
        3. Returns composite graph risk score (0.0 to 1.0)
        """
        device_accounts = []
        beneficiary_senders = []

        async with self.driver.session() as session:
            try:
                # 1. Check Device Sharing
                if device_id:
                    dev_query = """
                    MATCH (d:Device {id: $device_id})<-[:USES]-(a:Account)
                    RETURN collect(distinct a.id) as accounts
                    """
                    r_dev = await session.run(dev_query, device_id=str(device_id))
                    rec = await r_dev.single()
                    if rec:
                        device_accounts = rec["accounts"]

                # 2. Check Mule Beneficiary Multi-Account funneling
                ben_query = """
                MATCH (b:Beneficiary {id: $beneficiary_id})<-[:SENT_TO]-(:Transaction)<-[:MADE]-(a:Account)
                RETURN collect(distinct a.id) as senders
                """
                r_ben = await session.run(ben_query, beneficiary_id=str(beneficiary_id).lower().strip())
                rec_b = await r_ben.single()
                if rec_b:
                    beneficiary_senders = rec_b["senders"]

            except Exception as e:
                logger.error(f"Neo4j Error querying fraud ring: {e}")

        # Compute graph risk
        dev_shared = len(device_accounts)
        ben_fan_in = len(beneficiary_senders)

        graph_risk = 0.0
        ring_detected = False

        if dev_shared >= 3:
            graph_risk += 0.45
            ring_detected = True
        elif dev_shared == 2:
            graph_risk += 0.20

        if ben_fan_in >= 4:
            graph_risk += 0.50
            ring_detected = True
        elif ben_fan_in >= 2:
            graph_risk += 0.25

        # Overlap: Device accounts targeting this exact beneficiary
        overlap = set(device_accounts).intersection(set(beneficiary_senders))
        if len(overlap) >= 2:
            graph_risk = max(graph_risk, 0.92)
            ring_detected = True

        return {
            "graph_risk_score": round(min(1.0, graph_risk), 4),
            "ring_detected": ring_detected,
            "device_shared_count": dev_shared,
            "device_accounts": device_accounts,
            "beneficiary_sender_count": ben_fan_in,
            "beneficiary_senders": beneficiary_senders,
            "correlated_accounts": list(overlap)
        }

    async def get_account_risk_network(self, account_id: str) -> Dict[str, Any]:
        """
        Fetches 2-hop neighborhood graph for an account formatted for Cytoscape visualization.
        """
        query = """
        MATCH (a:Account {id: $account_id})
        OPTIONAL MATCH (a)-[r1:MADE]->(t:Transaction)-[r2:SENT_TO]->(b:Beneficiary)
        OPTIONAL MATCH (a)-[r3:USES]->(d:Device)
        RETURN a, collect(distinct t) as txns, collect(distinct b) as beneficiaries, collect(distinct d) as devices
        """
        nodes = []
        edges = []
        node_ids = set()

        def add_node(nid, label, ntype):
            if nid not in node_ids:
                node_ids.add(nid)
                nodes.append({"data": {"id": nid, "label": label, "type": ntype}})

        def add_edge(source, target, label):
            edges.append({"data": {"id": f"{source}_{target}_{label}", "source": source, "target": target, "label": label}})

        async with self.driver.session() as session:
            try:
                result = await session.run(query, account_id=str(account_id))
                rec = await result.single()
                if rec:
                    add_node(str(account_id), f"Account {account_id}", "Account")
                    for t in rec["txns"]:
                        if t and "id" in t:
                            tid = t["id"]
                            add_node(tid, f"Txn {tid}", "Transaction")
                            add_edge(str(account_id), tid, "MADE")
                    for b in rec["beneficiaries"]:
                        if b and "id" in b:
                            bid = b["id"]
                            add_node(bid, f"Beneficiary {bid}", "Beneficiary")
                            add_edge(str(account_id), bid, "SENT_TO")
                    for d in rec["devices"]:
                        if d and "id" in d:
                            did = d["id"]
                            add_node(did, f"Device {did}", "Device")
                            add_edge(str(account_id), did, "USES")
            except Exception as e:
                logger.error(f"Neo4j Error fetching account risk network: {e}")

        return {"nodes": nodes, "edges": edges}

