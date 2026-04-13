from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field

class TriggerType(str, Enum):
    EVENT = "event"          # EventBus Event
    STATE_CHANGE = "state"   # StateStore Change
    CRON = "cron"            # Schedule
    STARTUP = "startup"      # System Startup

class Comparator(str, Enum):
    EQUALS = "=="
    NOT_EQUALS = "!="
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    CONTAINS = "contains"

class Condition(BaseModel):
    """
    Evaluation Logic:
    If `key` in StateStore matches `value` via `comparator`.
    e.g. key="user.state", comparator="==", value="idle"
    """
    key: str
    comparator: Comparator = Comparator.EQUALS
    value: Any

class Action(BaseModel):
    """
    Execution Logic:
    Perform an operation.
    """
    type: str # "emit_event", "call_service", "log", "proactive_chat"
    payload: Dict[str, Any] = Field(default_factory=dict)
    delay_seconds: float = 0.0

class Trigger(BaseModel):
    type: TriggerType
    value: str # Event Name, State Key, or Cron Expression

class Rule(BaseModel):
    id: str
    name: str
    enabled: bool = True
    trigger: Trigger
    conditions: List[Condition] = Field(default_factory=list)
    actions: List[Action] = Field(default_factory=list)
    cooldown_seconds: float = 0.0 # Prevent spamming
    last_triggered: float = 0.0   # Runtime state
