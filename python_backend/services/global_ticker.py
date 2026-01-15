import asyncio
import logging
import time
from typing import List, Callable, Awaitable, Optional
from datetime import datetime

logger = logging.getLogger("GlobalTicker")

class TimeTicker:
    """
    Central Time Service (The Pulse).
    Provides a single asyncio loop for time-based events to prevent
    multiple `while True` loops across different plugins.
    
    Now emits events via EventBus in addition to direct callbacks.
    """
    def __init__(self, event_bus=None):
        self.running = False
        self.task = None
        self._second_subscribers: List[Callable[[datetime], Awaitable[None]]] = []
        self._minute_subscribers: List[Callable[[datetime], Awaitable[None]]] = []
        self._event_bus = event_bus  # EventBus integration
        
    def set_event_bus(self, bus):
        """Inject EventBus after construction (for late-binding)."""
        self._event_bus = bus
        
    def start(self):
        if self.running: return
        self.running = True
        self.task = asyncio.create_task(self._tick_loop())
        logger.info("鈴憋笍 Global Ticker Started")

    def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            
    def subscribe_seconds(self, callback: Callable[[datetime], Awaitable[None]]):
        """Callback must be an async function accepting (datetime)"""
        self._second_subscribers.append(callback)

    def subscribe_minutes(self, callback: Callable[[datetime], Awaitable[None]]):
        """Callback must be an async function accepting (datetime)"""
        self._minute_subscribers.append(callback)

    async def _tick_loop(self):
        last_minute = -1
        
        while self.running:
            try:
                now = datetime.now()
                
                # 1. Second Ticks (Legacy Subscribers)
                for sub in self._second_subscribers:
                    try:
                        # Fire and forget / or gather? 
                        # Better to spawn task to not block ticker
                        asyncio.create_task(sub(now))
                    except Exception as e:
                        logger.error(f"Error in second subscriber: {e}")

                # 1b. EventBus Tick Event (Phase 30)
                if self._event_bus:
                    await self._event_bus.emit("system.tick", {"timestamp": now.isoformat()})

                # 2. Minute Ticks
                if now.minute != last_minute:
                    last_minute = now.minute
                    for sub in self._minute_subscribers:
                        try:
                            asyncio.create_task(sub(now))
                        except Exception as e:
                            logger.error(f"Error in minute subscriber: {e}")
                    
                    # 2b. EventBus Minute Event
                    if self._event_bus:
                        await self._event_bus.emit("system.tick.minute", {"timestamp": now.isoformat()})
                
                # Align to next second
                await asyncio.sleep(1.0)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Global Ticker Error: {e}")
                await asyncio.sleep(1.0)

