"""intelligence init"""

from sales_transcriber.intelligence.analyzer import (
    ConversationAnalyzer,
)

from sales_transcriber.intelligence.models import (
    ConversationInsight,
)

from sales_transcriber.intelligence.recommendation_engine import (
    RecommendationEngine,
)

from sales_transcriber.intelligence.sales_coach import (
    SalesCoach,
)

from sales_transcriber.intelligence.opportunity_scoring import (
    OpportunityScoring,
)

from sales_transcriber.intelligence.conversation_state import (
    ConversationState,
)

from sales_transcriber.intelligence.state_manager import (
    ConversationStateManager,
)

from sales_transcriber.intelligence.speaker_detection import (
    SpeakerDetector,
    SpeakerSegment,
)
__all__ = [
    "ConversationAnalyzer",
    "ConversationInsight",
    "RecommendationEngine",
    "SalesCoach",
    "OpportunityScoring",
    "ConversationState",
    "ConversationStateManager",
    "SpeakerDetector",
    "SpeakerSegment",
]