import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from routers.deps import get_memory_service

logger = logging.getLogger("DebugRouter")
router = APIRouter(prefix="/debug", tags=["Debug"])


def _json_rows(rows: Any) -> List[Dict[str, Any]]:
    if not rows:
        return []
    output: List[Dict[str, Any]] = []
    for record in rows:
        if hasattr(record, "keys"):
            row = {}
            for key in record.keys():
                value = record[key]
                row[key] = value if isinstance(value, (str, int, float, bool, list, dict, type(None))) else str(value)
            output.append(row)
        elif isinstance(record, dict):
            output.append(record)
    return output


async def _query(memory, sql: str, params: dict | None = None) -> List[Dict[str, Any]]:
    rows = await memory.driver.query(sql, params or {})
    return _json_rows(rows)


@router.get("/brain_dump")
async def brain_dump(character_id: str = "hiyori", memory=Depends(get_memory_service)):
    """Return memory data used by local inspection panels."""
    try:
        cid = character_id.lower()
        history = await _query(
            memory,
            "SELECT * FROM conversation_log WHERE character_id = $cid ORDER BY created_at DESC LIMIT 100;",
            {"cid": cid},
        )
        facts = await _query(
            memory,
            "SELECT * FROM episodic_memory WHERE character_id = $cid ORDER BY created_at DESC LIMIT 100;",
            {"cid": cid},
        )
        nodes = await _query(
            memory,
            "SELECT * FROM knowledge_graph_nodes WHERE character_id = $cid LIMIT 200;",
            {"cid": cid},
        )
        edges = await _query(
            memory,
            "SELECT * FROM knowledge_graph_edges WHERE character_id = $cid LIMIT 300;",
            {"cid": cid},
        )
        return {
            "status": "success",
            "history": history,
            "facts": facts,
            "user_facts": facts,
            "graph": {"nodes": nodes, "edges": edges},
        }
    except Exception as exc:
        logger.error("Brain dump failed: %s", exc, exc_info=True)
        return {
            "status": "success",
            "history": [],
            "facts": [],
            "user_facts": [],
            "graph": {"nodes": [], "edges": []},
        }


@router.get("/processing_status")
async def processing_status(character_id: str = "hiyori", memory=Depends(get_memory_service)):
    """Return lightweight memory processing counters for inspection panels."""
    try:
        cid = character_id.lower()
        conversations = await _query(
            memory,
            "SELECT count(*) AS count FROM conversation_log WHERE character_id = $cid;",
            {"cid": cid},
        )
        unprocessed = await _query(
            memory,
            "SELECT count(*) AS count FROM conversation_log WHERE character_id = $cid AND is_processed = false;",
            {"cid": cid},
        )
        facts = await _query(
            memory,
            "SELECT count(*) AS count FROM episodic_memory WHERE character_id = $cid;",
            {"cid": cid},
        )

        def count(rows: List[Dict[str, Any]]) -> int:
            if not rows:
                return 0
            return int(rows[0].get("total") or rows[0].get("count") or 0)

        total_conversations = count(conversations)
        pending_conversations = count(unprocessed)
        total_facts = count(facts)
        threshold = 20

        return {
            "status": "success",
            "conversations": {
                "unprocessed": pending_conversations,
                "total": total_conversations,
                "threshold": threshold,
                "progress_percent": min(100, int((pending_conversations / threshold) * 100)) if threshold else 0,
            },
            "facts": {
                "user": {
                    "unconsolidated": 0,
                    "total": total_facts,
                    "threshold": threshold,
                    "progress_percent": 0,
                },
                "character": {
                    "unconsolidated": 0,
                    "total": total_facts,
                    "threshold": threshold,
                    "progress_percent": 0,
                },
            },
        }
    except Exception as exc:
        logger.error("Processing status failed: %s", exc, exc_info=True)
        return {
            "status": "success",
            "conversations": {"unprocessed": 0, "total": 0, "threshold": 20, "progress_percent": 0},
            "facts": {
                "user": {"unconsolidated": 0, "total": 0, "threshold": 20, "progress_percent": 0},
                "character": {"unconsolidated": 0, "total": 0, "threshold": 20, "progress_percent": 0},
            },
        }
