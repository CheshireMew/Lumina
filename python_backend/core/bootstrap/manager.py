
import logging
from typing import List
from .interface import Bootstrapper

logger = logging.getLogger("Bootstrap")

class BootstrapManager:
    def __init__(self):
        self.steps: List[Bootstrapper] = []

    def add(self, step: Bootstrapper):
        self.steps.append(step)
        return self

    async def start(self, container):
        logger.info("🚀 Starting Bootstrap Sequence...")
        for step in self.steps:
            try:
                logger.debug(f">> Bootstrapping: {step.name}")
                await step.bootstrap(container)
            except Exception as e:
                logger.critical(f"❌ Bootstrap Step '{step.name}' Failed: {e}")
                # We assume critical failure for now, unless step handles it internally
                raise e
        logger.info("✨ Bootstrap Sequence Complete.")
