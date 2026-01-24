from core.interfaces.plugin import BaseSystemPlugin

class HelloWorldPlugin(BaseSystemPlugin):
    @property
    def id(self):
        return "system.hello_world"

    @property
    def name(self):
        return "Hello World"

    def initialize(self, context):
        import logging
        logging.info("👋 HelloWorldPlugin: Initialize Called!")
        super().initialize(context)
        self.context = context
        
        logging.info("👋 HelloWorldPlugin: Registering Route /ping ...")
        # Register a generic route
        self.register_route(
            method="GET",
            path="/ping",
            handler=self.handle_ping
        )
        logging.info("👋 HelloWorldPlugin: Route Registered!")
        try:
            with open("hello_debug.txt", "w") as f:
                f.write("HelloWorld Initialized & Registered Route /ping")
        except: pass
        
    async def handle_ping(self):
        return {"message": "Pong from Hello World Plugin!", "plugin": self.id}
