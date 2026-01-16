from plugins.base import BaseSystemPlugin

class VerificationSensesApp(BaseSystemPlugin):
    @property
    def id(self) -> str:
        return "verify_senses"

    @property
    def name(self) -> str:
        return "Verification Senses"

    @property
    def category(self) -> str:
        return "system"
        
    @property
    def config_schema(self):
        return None

    def initialize(self, context):
        print("[Verification] Verify Senses App Initialized. Check drivers list!")
