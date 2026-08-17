"""Append-only CRM connector layer.

Connectors must never delete or overwrite CRM records. They append notes,
activities, tasks, or create suggested changes for user approval.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class CrmSyncResult:
    connector: str
    status: str
    message: str
    payload: dict


class BaseCrmConnector:
    name = "base"

    def append_meeting_insight(self, payload: dict) -> CrmSyncResult:
        raise NotImplementedError


class LocalJsonCrmConnector(BaseCrmConnector):
    name = "local_json"

    def __init__(self, output_dir: Path | None = None) -> None:
        base_dir = Path(os.getenv("LOCALAPPDATA") or Path.home())
        self._output_dir = output_dir or base_dir / "SalesIntelTranscriber" / "crm_outbox"
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def append_meeting_insight(self, payload: dict) -> CrmSyncResult:
        customer = (
            payload.get("customer", {}).get("customer_name")
            or payload.get("crm_append", {}).get("customer_name")
            or "cliente"
        )
        safe_customer = "".join(
            char.lower() if char.isalnum() else "-"
            for char in str(customer)
        ).strip("-") or "cliente"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = self._output_dir / f"{safe_customer}-{timestamp}.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return CrmSyncResult(
            connector=self.name,
            status="queued",
            message=(
                "Insight preparado en JSON append-only. "
                "Listo para enviarse a un CRM por API."
            ),
            payload={"path": str(path), "mode": "append_only"},
        )


def get_crm_connector(name: str | None = None) -> BaseCrmConnector:
    normalized = (name or os.getenv("CRM_CONNECTOR") or "local_json").strip().lower()
    if normalized == "local_json":
        return LocalJsonCrmConnector()
    return LocalJsonCrmConnector()
