import logging
import re
from typing import Any, List
from .models import Rule, Condition, Comparator
from .context import StateStore

logger = logging.getLogger("Automation.Engine")

class RuleEvaluator:
    """
    Stateless evaluator. Checks if a Rule satisfies current StateStore.
    """
    
    @staticmethod
    def evaluate(rule: Rule, store: StateStore) -> bool:
        """
        Returns True if ALL conditions in the rule are met.
        """
        if not rule.enabled:
            return False
            
        # Check cooldown
        # Runtime check usually happens in Service, but we can check last_triggered here if passed
        # For simplicity, Service handles side-effects (cooldown, execution).
        # We only check "Logic Conditions".
        
        if not rule.conditions:
            return True # No conditions = Always true if triggered
            
        for cond in rule.conditions:
            if not RuleEvaluator._check_condition(cond, store):
                return False
                
        return True

    @staticmethod
    def _check_condition(cond: Condition, store: StateStore) -> bool:
        current_val = store.get(cond.key)
        target_val = cond.value
        
        # Numeric conversion if possible for comparison
        # (e.g. CPU temp 45.0 > 40)
        try:
            if isinstance(current_val, (int, float, str)) and isinstance(target_val, (int, float, str)):
                 # Try to cast to float if one is number? 
                 # Python does this automatically for 45 > 40.0
                 pass
        except:
            pass
            
        try:
            if cond.comparator == Comparator.EQUALS:
                return current_val == target_val
            elif cond.comparator == Comparator.NOT_EQUALS:
                return current_val != target_val
            elif cond.comparator == Comparator.GT:
                return current_val > target_val
            elif cond.comparator == Comparator.LT:
                return current_val < target_val
            elif cond.comparator == Comparator.GTE:
                return current_val >= target_val
            elif cond.comparator == Comparator.LTE:
                return current_val <= target_val
            elif cond.comparator == Comparator.CONTAINS:
                if current_val is None: return False
                return target_val in current_val
            else:
                return False
        except TypeError:
            # e.g. None > 5
            return False
        except Exception as e:
            logger.warning(f"Condition Check Error [{cond.key} {cond.comparator} {cond.value}] vs {current_val}: {e}")
            return False
