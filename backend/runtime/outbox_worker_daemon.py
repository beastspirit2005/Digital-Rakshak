"""
Standalone Persistent Outbox Worker Daemon.
Enables containerized / dedicated worker execution outside Vercel Serverless.
Can be executed via:
    python -m runtime.outbox_worker_daemon
    or
    python -m services.outbox_worker_daemon
"""
import sys
import os
import signal
import asyncio
import logging
from typing import Optional

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from infrastructure.db.session import AsyncSessionLocal
from domain.services.outbox_worker import OutboxWorker
from core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("runtime.outbox_worker_daemon")


class OutboxWorkerDaemon:
    """
    Continuous persistent worker for dedicated container / VM environments.
    Executes outbox processing loops with graceful shutdown and dynamic idle backoff.
    """

    def __init__(
        self,
        worker_id: Optional[str] = None,
        idle_interval_sec: float = 5.0,
        max_idle_interval_sec: float = 15.0,
        batch_size: int = 10
    ):
        self.worker = OutboxWorker(worker_id=worker_id or f"DAEMON-{os.getpid()}")
        self.idle_interval_sec = idle_interval_sec
        self.max_idle_interval_sec = max_idle_interval_sec
        self.batch_size = batch_size
        self._running = False

    def handle_stop_signals(self):
        """Registers OS signal handlers for graceful shutdown."""
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.stop)
            except (NotImplementedError, AttributeError):
                # On Windows add_signal_handler is not fully implemented for all loops
                signal.signal(sig, lambda s, f: self.stop())

    def stop(self):
        logger.info(f"[{self.worker.worker_id}] Stop signal received. Shutting down gracefully...")
        self._running = False

    async def run(self):
        """Main execution loop."""
        self._running = True
        logger.info(
            f"[{self.worker.worker_id}] Starting Outbox Worker Daemon "
            f"(batch_size={self.batch_size}, idle_interval={self.idle_interval_sec}s)..."
        )
        current_sleep = self.idle_interval_sec

        while self._running:
            try:
                async with AsyncSessionLocal() as session:
                    summary = await self.worker.run_tick(
                        db=session,
                        batch_size=self.batch_size,
                        lease_seconds=getattr(settings, "OUTBOX_LEASE_SECONDS", 30),
                        timeout_budget_seconds=30.0,
                        trigger_type="DAEMON"
                    )

                claimed = summary.get("claimed", 0)
                remaining = summary.get("remaining_eligible", False)

                if claimed > 0:
                    logger.info(
                        f"[{self.worker.worker_id}] Processed batch: claimed={claimed}, "
                        f"processed={summary.get('processed')}, retry={summary.get('retry_scheduled')}, "
                        f"dead_letter={summary.get('dead_lettered')}"
                    )
                    # Backlog exists: continue immediately or with minimal yield
                    if remaining:
                        current_sleep = 0.5
                    else:
                        current_sleep = self.idle_interval_sec
                else:
                    # Queue is idle: apply gradual backoff up to max_idle_interval_sec
                    current_sleep = min(current_sleep * 1.5, self.max_idle_interval_sec)

            except Exception as e:
                logger.error(f"[{self.worker.worker_id}] Error in daemon iteration: {e}", exc_info=True)
                current_sleep = self.idle_interval_sec

            # Sleep in small slices to respond promptly to stop signal
            sleep_slices = int(current_sleep / 0.5)
            for _ in range(max(1, sleep_slices)):
                if not self._running:
                    break
                await asyncio.sleep(0.5)

        logger.info(f"[{self.worker.worker_id}] Outbox Worker Daemon stopped.")


async def main():
    daemon = OutboxWorkerDaemon()
    daemon.handle_stop_signals()
    await daemon.run()


if __name__ == "__main__":
    asyncio.run(main())
