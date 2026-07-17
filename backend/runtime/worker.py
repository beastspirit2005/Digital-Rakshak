import asyncio
import logging
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class BackgroundWorkerQueue:
    """
    Dedicated worker queue for asynchronous, heavy AI operations 
    (e.g., OCR on 100-page PDFs, Whisper transcription of 1-hour audio calls)
    so the FastAPI event loop isn't blocked.
    """
    
    def __init__(self, max_concurrent_tasks: int = 4):
        self._queue = asyncio.Queue()
        self._max_workers = max_concurrent_tasks
        self._workers = []
        
    async def enqueue(self, task_id: str, coro: Callable, *args, **kwargs) -> None:
        """Pushes a heavy coroutine to the background queue."""
        logger.info(f"Enqueued background task: {task_id}")
        await self._queue.put((task_id, coro, args, kwargs))
        
    async def _worker_loop(self, worker_id: int):
        """Internal loop pulling from the queue and executing."""
        logger.info(f"Background worker {worker_id} started.")
        while True:
            try:
                task_id, coro, args, kwargs = await self._queue.get()
                logger.info(f"[Worker {worker_id}] Executing task: {task_id}")
                
                try:
                    await coro(*args, **kwargs)
                except Exception as e:
                    logger.error(f"[Worker {worker_id}] Task {task_id} failed: {e}")
                    
                self._queue.task_done()
                logger.info(f"[Worker {worker_id}] Completed task: {task_id}")
            except asyncio.CancelledError:
                break
                
    def start(self):
        """Starts the worker pool."""
        for i in range(self._max_workers):
            task = asyncio.create_task(self._worker_loop(i))
            self._workers.append(task)
            
    async def stop(self):
        """Gracefully shuts down workers."""
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        
# Global Singleton instance
worker_queue = BackgroundWorkerQueue()
