from __future__ import annotations

import asyncio
import datetime
import logging
import time
from typing import Any, Dict, Optional
import httpx

from core.config import settings

logger = logging.getLogger(__name__)


class SupabaseKeepAlive:
    """
    Supabase Keep-Alive & Anti-Pause Daemon.
    
    Supabase Free tier projects automatically pause after 7 days of inactivity.
    This daemon sends authenticated heartbeat queries to Supabase PostgREST & Storage
    every 12 hours to continuously reset the inactivity timer and prevent automated pausing.
    """

    def __init__(self) -> None:
        self.last_ping_at: Optional[datetime.datetime] = None
        self.last_status: str = "initialized"
        self.last_latency_ms: float = 0.0
        self.consecutive_successes: int = 0
        self.total_pings: int = 0
        self.last_error: Optional[str] = None
        self.is_paused: bool = False
        self._daemon_task: Optional[asyncio.Task] = None

    @property
    def project_ref(self) -> str:
        """Extract project ref from Supabase URL (e.g. wsulobnicmdgtkpzostm)"""
        url = settings.SUPABASE_URL or ""
        if "://" in url:
            domain = url.split("://", 1)[1]
            return domain.split(".", 1)[0]
        return "unknown"

    @property
    def restore_url(self) -> str:
        return f"https://supabase.com/dashboard/project/{self.project_ref}"

    def get_api_key(self) -> Optional[str]:
        return settings.SUPABASE_KEY or os.environ.get("SUPABASE_ANON_KEY")

    async def ping(self) -> Dict[str, Any]:
        """
        Executes an authenticated ping against Supabase Storage and Auth services.
        Returns detailed diagnostics.
        """
        if not settings.SUPABASE_URL:
            return {
                "status": "skipped",
                "message": "SUPABASE_URL is not configured in environment.",
                "timestamp": datetime.datetime.utcnow().isoformat()
            }

        url = settings.SUPABASE_URL.rstrip("/")
        api_key = self.get_api_key()
        headers = {
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}"
        }

        self.total_pings += 1
        start = time.perf_counter()

        endpoints_to_test = [
            f"{url}/storage/v1/bucket",
            f"{url}/auth/v1/health"
        ]

        last_code = None
        error_detail = None
        success = False

        async with httpx.AsyncClient(timeout=15.0) as client:
            for target in endpoints_to_test:
                try:
                    resp = await client.get(target, headers=headers)
                    last_code = resp.status_code
                    
                    if resp.status_code in (200, 204):
                        success = True
                        break
                    elif resp.status_code == 544:
                        # Supabase DatabaseTimeout = Paused state
                        error_detail = "Supabase project database is PAUSED (HTTP 544 timeout)."
                        self.is_paused = True
                        break
                    elif resp.status_code == 401:
                        # Sometimes storage returns 401 if RLS is strict, but request still hits PostgREST
                        # Check auth/v1/health as fallback
                        error_detail = f"Endpoint {target} returned 401 (Auth issue): {resp.text[:100]}"
                    else:
                        error_detail = f"Endpoint {target} returned {resp.status_code}: {resp.text[:100]}"
                except Exception as exc:
                    error_detail = f"Connection failed to {target}: {str(exc)}"

        latency = round((time.perf_counter() - start) * 1000, 2)
        self.last_latency_ms = latency
        self.last_ping_at = datetime.datetime.utcnow()

        if success:
            self.last_status = "healthy"
            self.is_paused = False
            self.consecutive_successes += 1
            self.last_error = None
            logger.info(
                f"[Supabase Keep-Alive] Ping SUCCESS (Latency: {latency}ms). Project {self.project_ref} is ACTIVE."
            )
        else:
            if self.is_paused:
                self.last_status = "paused"
                logger.warning(
                    f"[Supabase Keep-Alive] Project {self.project_ref} is PAUSED. Restore at: {self.restore_url}"
                )
            else:
                self.last_status = "degraded"
                logger.warning(
                    f"[Supabase Keep-Alive] Ping returned status code {last_code}: {error_detail}"
                )
            self.consecutive_successes = 0
            self.last_error = error_detail

        return {
            "status": self.last_status,
            "project_ref": self.project_ref,
            "latency_ms": latency,
            "http_status": last_code,
            "is_paused": self.is_paused,
            "restore_url": self.restore_url if self.is_paused else None,
            "timestamp": self.last_ping_at.isoformat(),
            "total_pings": self.total_pings,
            "consecutive_successes": self.consecutive_successes,
            "error": self.last_error
        }

    async def start_daemon(self, interval_seconds: int = 43200) -> None:
        """
        Background daemon that wakes up periodically (default: every 12 hours)
        to send a keep-alive ping to Supabase.
        """
        logger.info(
            f"[Supabase Keep-Alive] Starting daemon for {self.project_ref}. Interval: {interval_seconds // 3600} hours."
        )
        # Immediate ping on startup
        try:
            await self.ping()
        except Exception as e:
            logger.error(f"[Supabase Keep-Alive] Initial ping failed: {e}")

        while True:
            try:
                await asyncio.sleep(interval_seconds)
                await self.ping()
            except asyncio.CancelledError:
                logger.info("[Supabase Keep-Alive] Daemon stopped.")
                break
            except Exception as e:
                logger.error(f"[Supabase Keep-Alive] Daemon cycle error: {e}")
                await asyncio.sleep(60)


# Global singleton
supabase_keepalive = SupabaseKeepAlive()
