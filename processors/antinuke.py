from logging import getLogger
from typing import Dict, List, Optional

log = getLogger("evict/processors")

def process_audit_threshold(
    action_history: List[Dict], 
    threshold: int,
    timeframe: int
) -> bool:
    """
    Process audit log threshold checks in a separate process.
    """
    log.info(f"Processing threshold check: {len(action_history)} actions against threshold {threshold}")
    recent_actions = len(action_history)
    log.info(f"Found {recent_actions} actions in last {timeframe}s")
    return recent_actions >= threshold

def process_whitelist_check(
    user_id: int,
    whitelist_ids: List[int]
) -> bool:
    """
    Process whitelist checks in a separate process.
    """
    log.info(f"Checking whitelist for user {user_id}")
    return user_id in whitelist_ids

def process_punishment_data(
    guild_data: Dict,
    module: str,
    action_type: str,
    details: Optional[str] = None
) -> Dict:
    """
    Process punishment data formatting in a separate process.
    """
    log.info(f"Processing punishment data for {module} {action_type}")
    
    punishment_data = {
        'reason': f"{module.title()} {action_type} attempt detected",
        'audit_reason': f"[Antinuke] {module.title()} {action_type} attempt"
    }
    
    if details:
        punishment_data['reason'] += f" | {details}"
        
    log.info(f"Processed punishment data: {punishment_data}")
    return punishment_data