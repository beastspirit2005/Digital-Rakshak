import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List
import logging
import asyncio

logger = logging.getLogger(__name__)

class ImmutableAuditLogger:
    """
    Append-only chronological audit ledger for all case and agent actions.
    Records are cryptographically hashed to prevent tampering.
    In a real system, this could write to WORM storage (Write Once Read Many).
    """
    
    def __init__(self, log_file: str = "audit_ledger.jsonl"):
        self._log_file = log_file
        self._lock = asyncio.Lock()
        
    def _hash_record(self, record: Dict[str, Any], previous_hash: str) -> str:
        record_str = json.dumps(record, sort_keys=True)
        return hashlib.sha256(f"{previous_hash}{record_str}".encode()).hexdigest()

    async def log_action(self, case_id: str, actor: str, action: str, details: Dict[str, Any]) -> str:
        """
        Appends an action to the immutable log. Returns the hash of the new record.
        """
        async with self._lock:
            # In a production environment, this would hit a DB table or blockchain.
            # Here, we simulate the append-only ledger using a local file.
            
            previous_hash = "0000000000000000000000000000000000000000000000000000000000000000"
            
            try:
                # Read last hash (this is inefficient for huge files, but works for PoC)
                with open(self._log_file, "r") as f:
                    lines = f.readlines()
                    if lines:
                        last_record = json.loads(lines[-1])
                        previous_hash = last_record.get("hash", previous_hash)
            except FileNotFoundError:
                pass
                
            record_body = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "case_id": case_id,
                "actor": actor,
                "action": action,
                "details": details
            }
            
            record_hash = self._hash_record(record_body, previous_hash)
            
            full_record = {
                "body": record_body,
                "previous_hash": previous_hash,
                "hash": record_hash
            }
            
            with open(self._log_file, "a") as f:
                f.write(json.dumps(full_record) + "\n")
                
            logger.info(f"AUDIT LOG [{case_id}] {actor} performed {action}. Hash: {record_hash[:8]}")
            return record_hash

    async def get_case_history(self, case_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves the chronological history for a specific case.
        """
        history = []
        try:
            with open(self._log_file, "r") as f:
                for line in f:
                    record = json.loads(line)
                    if record["body"].get("case_id") == case_id:
                        history.append(record["body"])
        except FileNotFoundError:
            pass
            
        return history
