"""models.py

ConversationInsight ampliado.

Los campos nuevos tienen default para no romper código existente
(OpportunityScoring, SalesCoach, RecommendationEngine) mientras se
migra la lógica hacia el LLM.
"""

from dataclasses import dataclass, field


@dataclass
class ConversationInsight:

    # --- Campos originales (no tocar) ---

    intent: str

    objections: list[str]

    primary_objection: str | None

    sentiment: str

    summary: str

    buying_signal: bool

    next_step: str | None

    sales_stage: str

    # --- Campos nuevos: scoring y riesgo calculados por el LLM ---

    opportunity_score: int = 0

    risk_level: str = "low"

    # --- Campos nuevos: extracción comercial estructurada ---

    pain_points: list[str] = field(default_factory=list)

    business_goals: list[str] = field(default_factory=list)

    competitors: list[str] = field(default_factory=list)

    budget_status: str | None = None

    timeline: str | None = None

    decision_maker: str | None = None

    # --- Campo nuevo: coaching generado por el LLM ---

    coach_advice: list[str] = field(default_factory=list)