
from core.interfaces.plugin import BaseSystemPlugin
import asyncio

class HelloWidgetPlugin(BaseSystemPlugin):
    @property
    def id(self) -> str:
        return "system.hello_widget"
        
    @property
    def name(self) -> str:
        return "Hello Widget"

    async def initialize(self, context):
        self.context = context
        self.logger = context.get_logger("HelloWidget")
        self.logger.info("👋 HelloWidget Initializing...")
        print("DEBUG: HelloWidget.initialize() called!") # Explicit print
        
        # Emit logic deferred slightly to ensure frontend is ready?
        # A proper system would wait for "frontend:connected" or just emit on startup + periodic.
        # For now, let's emit on startup.
        
        await self.register_widget()
        
    async def register_widget(self):
        # We assume the Asset Server serves "assets/index.html"
        widget_def = {
            "id": "hello_clock",
            "plugin_id": "system.hello_widget",
            "src": "/api/plugins/system.hello_widget/assets/index.html",
            "location": "sidebar_right",
            "title": "Stock Clock",
            "height": "160px"
        }
        
        self.logger.info(f"📤 Emitting ui:register_widget: {widget_def}")
        await self.context.bus.emit("ui:register_widget", widget_def)

    def terminate(self):
        self.logger.info("👋 HelloWidget Terminating...")
        # Optional: Remove widget
        # asyncio.create_task(self.context.bus.emit("ui:remove_widget", {"id": "hello_clock", "location": "sidebar_right"}))
