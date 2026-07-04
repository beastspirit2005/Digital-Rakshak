from fastapi import APIRouter, Depends, HTTPException, status
from infrastructure.graph.neo4j_client import IntelligenceGraph
from api.v1.users import get_current_admin
from core.security import decode_access_token
from fastapi.security import OAuth2PasswordBearer
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

async def get_current_official(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    role = payload.get("role")
    if role not in ["admin", "police", "cyber_cell", "bank_employee"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Official access required")
        
    return payload

@router.get("/network")
async def get_network(official_payload: dict = Depends(get_current_official)):
    """
    Returns the CTI graph nodes and links.
    Only accessible by officials and admins.
    """
    graph = IntelligenceGraph()
    try:
        query = """
        MATCH (n)-[r]->(m)
        RETURN 
            elementId(n) AS n_id, labels(n) AS n_labels, properties(n) AS n_props,
            elementId(m) AS m_id, labels(m) AS m_labels, properties(m) AS m_props,
            elementId(r) AS r_id, type(r) AS r_type
        LIMIT 500
        """
        nodes = {}
        links = []
        
        async with graph.driver.session() as session:
            result = await session.run(query)
            records = await result.data()
            
            for record in records:
                n_id = record['n_id']
                if n_id not in nodes:
                    n_label = record['n_labels'][0] if record['n_labels'] else "Unknown"
                    n_value = record['n_props'].get('id') or record['n_props'].get('value') or "Unknown"
                    nodes[n_id] = {
                        "id": n_id,
                        "label": n_label,
                        "value": n_value
                    }
                
                m_id = record['m_id']
                if m_id not in nodes:
                    m_label = record['m_labels'][0] if record['m_labels'] else "Unknown"
                    m_value = record['m_props'].get('id') or record['m_props'].get('value') or "Unknown"
                    nodes[m_id] = {
                        "id": m_id,
                        "label": m_label,
                        "value": m_value
                    }
                    
                links.append({
                    "source": n_id,
                    "target": m_id,
                    "type": record['r_type']
                })
                
        return {
            "nodes": list(nodes.values()),
            "links": links
        }
    except Exception as e:
        logger.error(f"Error fetching network: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch Intelligence Graph: {str(e)}")
    finally:
        await graph.close()
