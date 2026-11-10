"""
Forwarding proxy to runtime.outbox_worker_daemon.
"""
from runtime.outbox_worker_daemon import OutboxWorkerDaemon, main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
