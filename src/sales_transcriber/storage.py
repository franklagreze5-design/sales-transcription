"""Local persistence for customer conversation summaries."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from sales_transcriber.intelligence.models import ConversationInsight


@dataclass
class CustomerSummary:
    customer_name: str
    opportunity_score: int
    risk_level: str
    sales_stage: str
    sentiment: str
    buying_signal: bool
    budget_status: str | None
    timeline: str | None
    next_step: str | None
    summary: str
    pain_points: list[str]
    business_goals: list[str]
    updated_at: str


@dataclass
class CustomerProfile:
    customer_name: str
    seller_name: str
    industry: str
    company_size: str
    operations_people: str
    meeting_date: str
    updated_at: str


@dataclass
class MeetingSummary:
    id: int
    customer_name: str
    started_at: str
    ended_at: str | None
    meeting_date: str
    opportunity_score: int | None
    risk_level: str | None
    sales_stage: str | None
    budget_status: str | None
    timeline: str | None
    next_step: str | None
    summary: str | None


@dataclass
class TranscriptSegment:
    id: int
    meeting_id: int
    customer_name: str
    speaker: str | None
    text: str
    elapsed: float | None
    rms: float | None
    queue_size: int | None
    created_at: str


@dataclass
class CrmAppendEvent:
    id: int
    customer_name: str
    meeting_id: int | None
    connector: str
    payload: dict
    status: str
    created_at: str


def default_database_path() -> Path:
    """Return a per-user writable database path."""

    candidates = [
        Path(os.getenv("LOCALAPPDATA") or Path.home()) / "SalesIntelTranscriber",
        Path(sys.executable).resolve().parent / "data",
        Path.cwd() / "data",
        Path(tempfile.gettempdir()) / "SalesIntelTranscriber",
    ]

    for data_dir in candidates:
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            test_path = data_dir / ".write_test"
            test_path.write_text("ok", encoding="utf-8")
            test_path.unlink(missing_ok=True)
            return data_dir / "sales_intel.db"
        except OSError:
            continue

    return Path(tempfile.gettempdir()) / "sales_intel.db"


class CustomerStore:
    """Persist conversation summaries in a local SQLite database."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or default_database_path()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS customer_summaries (
                    customer_name TEXT PRIMARY KEY,
                    opportunity_score INTEGER NOT NULL,
                    risk_level TEXT NOT NULL,
                    sales_stage TEXT NOT NULL,
                    sentiment TEXT NOT NULL,
                    buying_signal INTEGER NOT NULL,
                    budget_status TEXT,
                    timeline TEXT,
                    next_step TEXT,
                    summary TEXT NOT NULL,
                    pain_points TEXT NOT NULL,
                    business_goals TEXT NOT NULL,
                    raw_insight TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS customer_profiles (
                    customer_name TEXT PRIMARY KEY,
                    seller_name TEXT NOT NULL DEFAULT '',
                    industry TEXT NOT NULL DEFAULT '',
                    company_size TEXT NOT NULL DEFAULT '',
                    operations_people TEXT NOT NULL DEFAULT '',
                    meeting_date TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                )
                """
            )
            profile_columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(customer_profiles)").fetchall()
            }
            if "seller_name" not in profile_columns:
                conn.execute(
                    "ALTER TABLE customer_profiles ADD COLUMN seller_name TEXT NOT NULL DEFAULT ''"
                )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS customer_meetings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    meeting_date TEXT NOT NULL DEFAULT '',
                    opportunity_score INTEGER,
                    risk_level TEXT,
                    sales_stage TEXT,
                    budget_status TEXT,
                    timeline TEXT,
                    next_step TEXT,
                    summary TEXT,
                    raw_insight TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS transcript_segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meeting_id INTEGER NOT NULL,
                    customer_name TEXT NOT NULL,
                    speaker TEXT,
                    text TEXT NOT NULL,
                    elapsed REAL,
                    rms REAL,
                    queue_size INTEGER,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS crm_append_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT NOT NULL,
                    meeting_id INTEGER,
                    connector TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def save_profile(self, customer_name: str, context: dict) -> CustomerProfile:
        name = customer_name.strip() or "Cliente sin nombre"
        updated_at = datetime.now().isoformat(timespec="seconds")
        profile = CustomerProfile(
            customer_name=name,
            seller_name=str(context.get("seller_name", "")).strip(),
            industry=str(context.get("industry", "")).strip(),
            company_size=str(context.get("company_size", "")).strip(),
            operations_people=str(context.get("operations_people", "")).strip(),
            meeting_date=str(context.get("meeting_date", "")).strip(),
            updated_at=updated_at,
        )

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO customer_profiles (
                    customer_name,
                    seller_name,
                    industry,
                    company_size,
                    operations_people,
                    meeting_date,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(customer_name) DO UPDATE SET
                    seller_name=excluded.seller_name,
                    industry=excluded.industry,
                    company_size=excluded.company_size,
                    operations_people=excluded.operations_people,
                    meeting_date=excluded.meeting_date,
                    updated_at=excluded.updated_at
                """,
                (
                    profile.customer_name,
                    profile.seller_name,
                    profile.industry,
                    profile.company_size,
                    profile.operations_people,
                    profile.meeting_date,
                    profile.updated_at,
                ),
            )

        return profile

    def get_profile(self, customer_name: str) -> CustomerProfile | None:
        name = customer_name.strip() or "Cliente sin nombre"
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT customer_name, seller_name, industry, company_size, operations_people,
                    meeting_date, updated_at
                FROM customer_profiles
                WHERE customer_name = ?
                """,
                (name,),
            ).fetchone()

        if not row:
            return None
        return CustomerProfile(*row)

    def create_meeting(self, customer_name: str, context: dict) -> int:
        name = customer_name.strip() or "Cliente sin nombre"
        started_at = datetime.now().isoformat(timespec="seconds")
        meeting_date = str(context.get("meeting_date", "")).strip()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO customer_meetings (
                    customer_name,
                    started_at,
                    meeting_date
                )
                VALUES (?, ?, ?)
                """,
                (name, started_at, meeting_date),
            )
            return int(cursor.lastrowid)

    def finish_meeting(
        self,
        meeting_id: int,
        insight: ConversationInsight | None = None,
    ) -> None:
        ended_at = datetime.now().isoformat(timespec="seconds")
        if insight is None:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE customer_meetings SET ended_at = ? WHERE id = ?",
                    (ended_at, meeting_id),
                )
            return

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE customer_meetings
                SET ended_at = ?,
                    opportunity_score = ?,
                    risk_level = ?,
                    sales_stage = ?,
                    budget_status = ?,
                    timeline = ?,
                    next_step = ?,
                    summary = ?,
                    raw_insight = ?
                WHERE id = ?
                """,
                (
                    ended_at,
                    insight.opportunity_score,
                    insight.risk_level,
                    insight.sales_stage,
                    insight.budget_status,
                    insight.timeline,
                    insight.next_step,
                    insight.summary,
                    json.dumps(asdict(insight), ensure_ascii=False),
                    meeting_id,
                ),
            )

    def save_segment(
        self,
        meeting_id: int,
        customer_name: str,
        speaker: str | None,
        text: str,
        elapsed: float | None,
        rms: float | None,
        queue_size: int | None,
    ) -> TranscriptSegment:
        name = customer_name.strip() or "Cliente sin nombre"
        created_at = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO transcript_segments (
                    meeting_id,
                    customer_name,
                    speaker,
                    text,
                    elapsed,
                    rms,
                    queue_size,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meeting_id,
                    name,
                    speaker,
                    text,
                    elapsed,
                    rms,
                    queue_size,
                    created_at,
                ),
            )
            segment_id = int(cursor.lastrowid)

        return TranscriptSegment(
            id=segment_id,
            meeting_id=meeting_id,
            customer_name=name,
            speaker=speaker,
            text=text,
            elapsed=elapsed,
            rms=rms,
            queue_size=queue_size,
            created_at=created_at,
        )

    def save_insight(
        self,
        customer_name: str,
        insight: ConversationInsight,
    ) -> CustomerSummary:
        name = customer_name.strip() or "Cliente sin nombre"
        updated_at = datetime.now().isoformat(timespec="seconds")
        pain_points = json.dumps(insight.pain_points, ensure_ascii=False)
        business_goals = json.dumps(insight.business_goals, ensure_ascii=False)
        raw_insight = json.dumps(asdict(insight), ensure_ascii=False)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO customer_summaries (
                    customer_name,
                    opportunity_score,
                    risk_level,
                    sales_stage,
                    sentiment,
                    buying_signal,
                    budget_status,
                    timeline,
                    next_step,
                    summary,
                    pain_points,
                    business_goals,
                    raw_insight,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(customer_name) DO UPDATE SET
                    opportunity_score=excluded.opportunity_score,
                    risk_level=excluded.risk_level,
                    sales_stage=excluded.sales_stage,
                    sentiment=excluded.sentiment,
                    buying_signal=excluded.buying_signal,
                    budget_status=excluded.budget_status,
                    timeline=excluded.timeline,
                    next_step=excluded.next_step,
                    summary=excluded.summary,
                    pain_points=excluded.pain_points,
                    business_goals=excluded.business_goals,
                    raw_insight=excluded.raw_insight,
                    updated_at=excluded.updated_at
                """,
                (
                    name,
                    insight.opportunity_score,
                    insight.risk_level,
                    insight.sales_stage,
                    insight.sentiment,
                    int(insight.buying_signal),
                    insight.budget_status,
                    insight.timeline,
                    insight.next_step,
                    insight.summary,
                    pain_points,
                    business_goals,
                    raw_insight,
                    updated_at,
                ),
            )

        return CustomerSummary(
            customer_name=name,
            opportunity_score=insight.opportunity_score,
            risk_level=insight.risk_level,
            sales_stage=insight.sales_stage,
            sentiment=insight.sentiment,
            buying_signal=insight.buying_signal,
            budget_status=insight.budget_status,
            timeline=insight.timeline,
            next_step=insight.next_step,
            summary=insight.summary,
            pain_points=insight.pain_points,
            business_goals=insight.business_goals,
            updated_at=updated_at,
        )

    def list_customers(self) -> list[CustomerSummary]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    customer_name,
                    opportunity_score,
                    risk_level,
                    sales_stage,
                    sentiment,
                    buying_signal,
                    budget_status,
                    timeline,
                    next_step,
                    summary,
                    pain_points,
                    business_goals,
                    updated_at
                FROM customer_summaries
                ORDER BY updated_at DESC
                """
            ).fetchall()

        return [
            CustomerSummary(
                customer_name=row[0],
                opportunity_score=row[1],
                risk_level=row[2],
                sales_stage=row[3],
                sentiment=row[4],
                buying_signal=bool(row[5]),
                budget_status=row[6],
                timeline=row[7],
                next_step=row[8],
                summary=row[9],
                pain_points=json.loads(row[10]),
                business_goals=json.loads(row[11]),
                updated_at=row[12],
            )
            for row in rows
        ]

    def list_profiles(self) -> list[CustomerProfile]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT customer_name, seller_name, industry, company_size, operations_people,
                    meeting_date, updated_at
                FROM customer_profiles
                ORDER BY updated_at DESC
                """
            ).fetchall()

        return [CustomerProfile(*row) for row in rows]

    def list_meetings(
        self,
        customer_name: str | None = None,
        limit: int = 50,
    ) -> list[MeetingSummary]:
        params: tuple = (limit,)
        where = ""
        if customer_name:
            where = "WHERE customer_name = ?"
            params = (customer_name.strip() or "Cliente sin nombre", limit)

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    id,
                    customer_name,
                    started_at,
                    ended_at,
                    meeting_date,
                    opportunity_score,
                    risk_level,
                    sales_stage,
                    budget_status,
                    timeline,
                    next_step,
                    summary
                FROM customer_meetings
                {where}
                ORDER BY started_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()

        return [MeetingSummary(*row) for row in rows]

    def list_segments(
        self,
        customer_name: str | None = None,
        meeting_id: int | None = None,
    ) -> list[TranscriptSegment]:
        clauses = []
        params: list = []
        if customer_name:
            clauses.append("customer_name = ?")
            params.append(customer_name.strip() or "Cliente sin nombre")
        if meeting_id is not None:
            clauses.append("meeting_id = ?")
            params.append(meeting_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    id,
                    meeting_id,
                    customer_name,
                    speaker,
                    text,
                    elapsed,
                    rms,
                    queue_size,
                    created_at
                FROM transcript_segments
                {where}
                ORDER BY created_at ASC, id ASC
                """,
                tuple(params),
            ).fetchall()

        return [TranscriptSegment(*row) for row in rows]

    def meeting_export_payload(
        self,
        customer_name: str | None = None,
        meeting_id: int | None = None,
    ) -> dict:
        meetings = self.list_meetings(customer_name=customer_name, limit=200)
        if meeting_id is not None:
            meetings = [meeting for meeting in meetings if meeting.id == meeting_id]
        meeting = meetings[0] if meetings else None
        name = (
            meeting.customer_name
            if meeting
            else (customer_name or "Cliente sin nombre").strip() or "Cliente sin nombre"
        )
        profile = self.get_profile(name)
        summaries = {summary.customer_name: summary for summary in self.list_customers()}
        summary = summaries.get(name)
        segments = self.list_segments(customer_name=name, meeting_id=meeting.id if meeting else None)

        return {
            "schema": "sales_coach_ai.crm_append.v1",
            "mode": "append_only",
            "customer": asdict(profile) if profile else {"customer_name": name},
            "meeting": asdict(meeting) if meeting else None,
            "insight": asdict(summary) if summary else None,
            "crm_append": {
                "summary": summary.summary if summary else "",
                "next_step": summary.next_step if summary else "",
                "risk_level": summary.risk_level if summary else "",
                "opportunity_score": summary.opportunity_score if summary else 0,
                "pain_points": summary.pain_points if summary else [],
                "business_goals": summary.business_goals if summary else [],
                "follow_up_date": summary.timeline if summary else "",
                "suggested_changes": [],
                "policy": "Never delete or overwrite CRM data. Add a new note/activity or create suggestions for approval.",
            },
            "transcript_segments": [asdict(segment) for segment in segments],
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }

    def append_crm_event(
        self,
        customer_name: str,
        meeting_id: int | None,
        connector: str,
        payload: dict,
        status: str,
    ) -> CrmAppendEvent:
        name = customer_name.strip() or "Cliente sin nombre"
        created_at = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO crm_append_events (
                    customer_name,
                    meeting_id,
                    connector,
                    payload,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    meeting_id,
                    connector,
                    json.dumps(payload, ensure_ascii=False),
                    status,
                    created_at,
                ),
            )
            event_id = int(cursor.lastrowid)

        return CrmAppendEvent(
            id=event_id,
            customer_name=name,
            meeting_id=meeting_id,
            connector=connector,
            payload=payload,
            status=status,
            created_at=created_at,
        )



