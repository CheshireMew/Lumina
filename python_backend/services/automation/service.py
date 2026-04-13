import logging
import asyncio
import time
from typing import Dict, List, Any
from .models import Rule, TriggerType, Action, Trigger
from .context import StateStore
from .engine import RuleEvaluator

logger = logging.getLogger("Automation.Service")

class AutomationService:
    """
    Central Orchestrator for ECA Engine.
    - Manages StateStore
    - Manages Rules
    - Subscribes to EventBus -> Updates State / Triggers Rules
    - Executes Actions
    """
    def __init__(self, services_container):
        self.services = services_container
        self.state = StateStore()
        self.rules: Dict[str, Rule] = {}
        
        # Internal Indexes for fast lookup
        self._event_triggers: Dict[str, List[str]] = {} # event_name -> [rule_id]
        self._state_triggers: Dict[str, List[str]] = {} # state_key -> [rule_id]
        
        self.is_running = False

    def start(self):
        """Bind to EventBus and start listeners"""
        if self.is_running: return
        
        # 1. Bind EventBus
        bus = getattr(self.services, 'event_bus', None)
        if bus:
            # Subscribe to ALL events to update state or trigger rules? 
            # Subscribing to "*" might be expensive.
            # Ideally we only subscribe to events mentioned in rules.
            # For now, let's assume we register specific listeners.
            pass
            
        # 2. Bind State Listener
        self.state.subscribe(self._on_state_change)
        
        self.is_running = True
        logger.info("🧠 ECA Engine Started")
        
        # 3. Fire Startup Rules
        self._fire_trigger(TriggerType.STARTUP, "startup")

    def register_rule(self, rule: Rule):
        """Add a rule to the engine."""
        self.rules[rule.id] = rule
        
        # Indexing
        if rule.trigger.type == TriggerType.EVENT:
            evt = rule.trigger.value
            if evt not in self._event_triggers:
                 self._event_triggers[evt] = []
                 # Subscribe to bus if not already
                 self._subscribe_to_event(evt)
            self._event_triggers[evt].append(rule.id)
            
        elif rule.trigger.type == TriggerType.STATE_CHANGE:
            if rule.trigger.value not in self._state_triggers:
                self._state_triggers[rule.trigger.value] = []
            self._state_triggers[rule.trigger.value].append(rule.id)
            
        logger.info(f"Registered Rule: {rule.name}")

    def load_rules_from_yaml(self, path: str):
        # TODO: Implement YAML loader
        pass

    def _subscribe_to_event(self, event_name: str):
        bus = getattr(self.services, 'event_bus', None)
        if bus:
            # Lambda capture issue? use partial or def
            async def handler(event):
                await self._on_event_trigger(event_name, event)
            bus.subscribe(event_name, handler)

    async def _on_event_trigger(self, event_name: str, payload: Any):
        """Handle EventBus triggers"""
        # 1. Update State (Optional: Some events auto-update state?)
        # For now, assume Event Rules are pure triggers.
        
        # 2. Match Rules
        rule_ids = self._event_triggers.get(event_name, [])
        for rid in rule_ids:
            await self._evaluate_and_execute(rid, payload)

    def _on_state_change(self, key: str, old_val: Any, new_val: Any):
        """Handle StateStore triggers"""
        rule_ids = self._state_triggers.get(key, [])
        if not rule_ids: return
        
        # Don't block state lock, run async
        asyncio.create_task(self._process_state_rules(rule_ids, new_val))

    async def _process_state_rules(self, rule_ids: List[str], context: Any):
        for rid in rule_ids:
            await self._evaluate_and_execute(rid, context)
            
    def _fire_trigger(self, trigger_type: TriggerType, value: str):
        """Manual trigger (e.g. startup, cron)"""
        # Linear scan for STARTUP/CRON (Optimization: Index them too)
        for rule in self.rules.values():
            if rule.trigger.type == trigger_type and rule.trigger.value == value:
                asyncio.create_task(self._evaluate_and_execute(rule.id, None))

    async def _evaluate_and_execute(self, rule_id: str, context: Any):
        rule = self.rules.get(rule_id)
        if not rule or not rule.enabled: return
        
        # Cooldown Check
        now = time.time()
        if now - rule.last_triggered < rule.cooldown_seconds:
            return

        # Condition Check
        if RuleEvaluator.evaluate(rule, self.state):
            logger.info(f"⚡ Rule Triggered: {rule.name}")
            rule.last_triggered = now
            await self._execute_actions(rule.actions, context)

    async def _execute_actions(self, actions: List[Action], context: Any):
        for action in actions:
            if action.delay_seconds > 0:
                await asyncio.sleep(action.delay_seconds)
            
            try:
                if action.type == "log":
                    logger.info(f"👉 [Rule Action] {action.payload}")
                
                elif action.type == "emit_event":
                    bus = getattr(self.services, 'event_bus', None)
                    if bus:
                        from core.protocol import EventPacket # Simplified
                        # bus.emit(...) - TODO: Construct proper packet
                        pass
                
                elif action.type == "proactive_chat":
                    logger.info(f"🗣️ Proactive Chat Triggered: {action.payload}")
                    # Call LLM Service ...
            except Exception as e:
                logger.error(f"Action Execution Error: {e}")
