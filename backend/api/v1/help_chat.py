from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from typing import Dict, Any, List
import json
import logging
import httpx
import ollama
import asyncio
from core.config import settings
from infrastructure.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from domain.models.settings import PlatformSettings

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # Maps role -> {client_id -> WebSocket}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {
            "citizen": {},
            "admin": {}
        }
        
    async def connect(self, websocket: WebSocket, client_id: str, role: str):
        await websocket.accept()
        if role not in self.active_connections:
            self.active_connections[role] = {}
        self.active_connections[role][client_id] = websocket
        logger.info(f"{role} {client_id} connected to Help Chat.")

    def disconnect(self, client_id: str, role: str):
        if role in self.active_connections and client_id in self.active_connections[role]:
            del self.active_connections[role][client_id]
            logger.info(f"{role} {client_id} disconnected from Help Chat.")

    async def send_personal_message(self, message: dict, client_id: str, role: str):
        if role in self.active_connections and client_id in self.active_connections[role]:
            ws = self.active_connections[role][client_id]
            await ws.send_json(message)

    async def broadcast_to_role(self, message: dict, role: str):
        if role in self.active_connections:
            for connection in self.active_connections[role].values():
                await connection.send_json(message)

    def is_admin_online(self) -> bool:
        return len(self.active_connections.get("admin", {})) > 0

manager = ConnectionManager()

@router.get("/admin-status")
async def get_admin_status():
    """Checks if any admin is currently connected to the websocket."""
    return {"is_admin_online": manager.is_admin_online()}

@router.get("/chat-settings")
async def get_chat_settings(db: AsyncSession = Depends(get_db)):
    """Returns the chat settings to determine if local mode is forced."""
    result = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
    db_settings = result.scalar_one_or_none()
    
    force_local = settings.FORCE_LOCAL_INFERENCE
    if db_settings:
        force_local = db_settings.force_local_inference or db_settings.default_ai_mode == "ollama"
        
    return {"force_local_inference": force_local}

async def stream_ai_response(messages: List[dict], db: AsyncSession, requested_model: str = None):
    # Check platform settings for local enforcement
    result = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
    db_settings = result.scalar_one_or_none()
    
    force_local = settings.FORCE_LOCAL_INFERENCE
    if db_settings:
        force_local = db_settings.force_local_inference or db_settings.default_ai_mode == "ollama"

    system_prompt = {
        "role": "system",
        "content": "You are the Digital Rakshak AI Support Agent. Answer questions concisely and politely about reporting cyber crimes and using the platform. Do NOT mention you are an AI model like Gemini, Groq, or Ollama."
    }
    
    formatted_messages = [system_prompt] + messages

    if force_local:
        # Use Ollama
        model_to_use = requested_model if requested_model else 'mistral'
        try:
            client = ollama.AsyncClient()
            async for chunk in await client.chat(model=model_to_use, messages=formatted_messages, stream=True):
                if chunk and 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']
        except Exception as e:
            logger.error(f"Ollama failed: {e}")
            yield "Sorry, our local AI system is currently unavailable. Please try again later or escalate to a human."
    else:
        # Use Groq
        if not settings.GROQ_API_KEY:
            yield "Groq API key is missing. Please configure it in the backend settings."
            return
        
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": formatted_messages,
                        "temperature": 0.3,
                        "stream": True
                    },
                    timeout=30.0
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                data = json.loads(line[6:])
                                content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content:
                                    yield content
                            except Exception:
                                pass
        except Exception as e:
            logger.error(f"Groq failed: {e}")
            yield "Sorry, our cloud AI system is currently experiencing issues."

@router.websocket("/ws/{role}/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    role: str, 
    client_id: str
):
    valid_roles = ["citizen", "admin", "police", "cyber_cell", "banker", "bank_employee"]
    if role not in valid_roles:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, client_id, role)
    
    # Store chat history in memory for this session (for AI context)
    chat_history = []
    active_stream_task = None
    
    try:
        while True:
            data_str = await websocket.receive_text()
            try:
                data = json.loads(data_str)
            except Exception:
                continue

            msg_type = data.get("type", "chat")
            content = data.get("content", "")

            if msg_type == "stop_chat":
                if active_stream_task and not active_stream_task.done():
                    active_stream_task.cancel()
                continue

            if msg_type == "escalate":
                # Citizen wants a human
                if manager.is_admin_online():
                    # Notify admins
                    await manager.broadcast_to_role({
                        "type": "escalation_request",
                        "client_id": client_id,
                        "content": "A citizen has requested live support."
                    }, "admin")
                    await manager.send_personal_message({
                        "type": "system",
                        "content": "An admin has been notified and will join shortly."
                    }, client_id, "citizen")
                else:
                    await manager.send_personal_message({
                        "type": "fallback_ticket",
                        "content": "No admins are currently online. Please submit a support ticket."
                    }, client_id, "citizen")
            
            elif msg_type == "admin_reply":
                # Admin replies to a citizen
                target_client = data.get("target_client_id")
                if target_client:
                    await manager.send_personal_message({
                        "type": "human_chat",
                        "content": content,
                        "sender": "Admin"
                    }, target_client, "citizen")
                    # Echo back to admin so they see it
                    await manager.send_personal_message({
                        "type": "human_chat",
                        "content": content,
                        "sender": "Admin",
                        "target_client_id": target_client
                    }, client_id, "admin")
                    
            elif msg_type == "chat":
                # Standard AI chat
                requested_model = data.get("model")
                chat_history.append({"role": "user", "content": content})
                
                # Keep history manageable (last 10 messages)
                if len(chat_history) > 10:
                    chat_history = chat_history[-10:]

                if active_stream_task and not active_stream_task.done():
                    active_stream_task.cancel()
                
                async def generate_and_stream(req_model, history_copy):
                    from infrastructure.db.session import AsyncSessionLocal
                    full_reply = ""
                    try:
                        async with AsyncSessionLocal() as session:
                            async for chunk in stream_ai_response(history_copy, session, req_model):
                                full_reply += chunk
                                await manager.send_personal_message({
                                    "type": "ai_chat_chunk",
                                    "content": chunk
                                }, client_id, role)
                        
                        chat_history.append({"role": "assistant", "content": full_reply})
                        await manager.send_personal_message({
                            "type": "ai_chat_done"
                        }, client_id, role)
                    except asyncio.CancelledError:
                        logger.info(f"Stream cancelled for client {client_id}")
                        chat_history.append({"role": "assistant", "content": full_reply + " [Interrupted]"})
                        await manager.send_personal_message({
                            "type": "ai_chat_done"
                        }, client_id, role)
                    except Exception as e:
                        logger.error(f"Error in stream task: {e}", exc_info=True)
                        await manager.send_personal_message({
                            "type": "ai_chat",
                            "content": f"Sorry, an internal error occurred: {str(e)}"
                        }, client_id, role)
                        await manager.send_personal_message({
                            "type": "ai_chat_done"
                        }, client_id, role)

                active_stream_task = asyncio.create_task(generate_and_stream(requested_model, list(chat_history)))

    except WebSocketDisconnect:
        manager.disconnect(client_id, role)
