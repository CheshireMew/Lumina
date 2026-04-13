"""
In-Memory Job Queue
===================
Implementation of IJobQueue using asyncio.PriorityQueue.
"""

import asyncio
import logging
from typing import Optional
from core.interfaces.queue import IJobQueue, Job

logger = logging.getLogger("MemoryQueue")

class MemoryJobQueue(IJobQueue):
    def __init__(self):
        self._queue = asyncio.PriorityQueue()

    async def enqueue(self, job: Job) -> bool:
        await self._queue.put(job)
        return True

    def enqueue_sync(self, job: Job, loop: asyncio.AbstractEventLoop):
        """Thread-safe enqueue for synchronous callbacks (e.g. from sounddevice)."""
        try:
            loop.call_soon_threadsafe(self._queue.put_nowait, job)
        except Exception as e:
            logger.error(f"Failed to enqueue job {job.id}: {e}")

    async def dequeue(self) -> Optional[Job]:
        return await self._queue.get()
    
    def size(self) -> int:
        return self._queue.qsize()

    def task_done(self):
        self._queue.task_done()
