"""models.py"""

from dataclasses import dataclass


@dataclass
class ConversationInsight:

    intent: str

    objections: list[str]

    primary_objection: str | None

    sentiment: str

    summary: str

    buying_signal: bool

    next_step: str | None

    sales_stage: str