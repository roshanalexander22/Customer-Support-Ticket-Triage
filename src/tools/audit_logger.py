"""Structured Audit Logging Tool for Workflow Telemetry and Traceability."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List
from src.config import LOGS_DIR, SAVE_AUDIT_LOGS
from src.state import AuditLogEntry


class AuditLoggerTool:
    """Records immutable audit logs of agent deliberations, tool calls, and state changes."""

    def __init__(self, log_dir: Path = LOGS_DIR):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        audit_trail: List[AuditLogEntry],
        step: str,
        agent: str,
        action: str,
        details: Dict[str, Any],
        duration_ms: float = 0.0,
        status: str = "SUCCESS"
    ) -> AuditLogEntry:
        """Create and append an audit record to the workflow trace."""
        entry: AuditLogEntry = {
            "step": step,
            "agent": agent,
            "action": action,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_ms": round(duration_ms, 2),
            "status": status
        }
        audit_trail.append(entry)
        return entry

    def persist_trace(self, ticket_id: str, state: Dict[str, Any]) -> Path:
        """Persist full execution state and audit trail to JSON for auditing."""
        if not SAVE_AUDIT_LOGS:
            return self.log_dir / f"ticket_{ticket_id}.json"

        file_path = self.log_dir / f"ticket_{ticket_id}.json"
        
        # Serialize state safely
        serializable_state = {}
        for k, v in state.items():
            try:
                json.dumps(v)
                serializable_state[k] = v
            except (TypeError, OverflowError):
                serializable_state[k] = str(v)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(serializable_state, f, indent=2)

        return file_path


# Global singleton instance
audit_logger_tool = AuditLoggerTool()

