from pydantic import BaseModel, Field
from typing import Literal


class TicketClassification(BaseModel):
    """Structured classification of an incoming support ticket."""

    category: Literal[
        "billing", "technical", "account", "feature_request", "other"
    ] = Field(description="The primary category this ticket falls into")

    urgency: Literal["low", "medium", "high", "critical"] = Field(
        description="How urgently this needs a response, based on impact and tone"
    )

    sentiment: Literal["neutral", "frustrated", "angry"] = Field(
        description="The emotional tone of the customer's message"
    )

    auto_resolve_eligible: bool = Field(
        description=(
            "True only if this is a common, well-documented question "
            "(e.g. billing FAQ, password reset, standard account question) "
            "that a knowledge base article could fully answer. "
            "False for anything technical/bug-related, ambiguous, or where "
            "the customer seems to need a human judgment call."
        )
    )

    reasoning: str = Field(
        description="One sentence explaining why you classified it this way"
    )


class ConfidenceAssessment(BaseModel):
    """
    Step 5: rates how confident the system should be that a drafted
    response fully and correctly resolves the ticket, grounded strictly
    in what the KB excerpts actually support.
    """

    confidence_score: int = Field(
        ge=0,
        le=100,
        description=(
            "0-100. How confident are you that this response fully and "
            "accurately resolves the customer's ticket, using ONLY what "
            "the knowledge base excerpts support? Score low if the draft "
            "had to guess, generalize beyond the excerpts, or if the "
            "ticket has any account-specific action (refunds, charges, "
            "data recovery) that a generic KB answer can't safely cover."
        )
    )

    reasoning: str = Field(
        description="One sentence explaining the score -- what specifically "
        "makes you confident or uncertain"
    )


class EscalationSummary(BaseModel):
    """
    Step 6: what a human agent sees when a ticket lands in their queue --
    either because it was never auto-resolve-eligible, or because a draft
    was written but confidence scoring flagged it for review.
    """

    summary: str = Field(
        description="2-3 sentence summary of what the customer needs and "
        "why this needed a human, written for a support agent skimming a queue"
    )

    recommended_next_step: str = Field(
        description="One concrete action the agent should take first "
        "(e.g. 'Verify the duplicate charge in the billing system and "
        "process a refund' or 'Check server logs for the missing board')"
    )
