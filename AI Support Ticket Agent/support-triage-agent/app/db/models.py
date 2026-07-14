"""
Step 7: SQLAlchemy model for persisted ticket outcomes.
One row per ticket processed, capturing every stage of the pipeline --
classification, retrieval, drafting, confidence scoring, and the final
routing decision -- so results survive after the script exits and can
feed a dashboard later.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Text, Boolean, Integer, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TicketRecord(Base):
    __tablename__ = "ticket_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Original ticket
    subject: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)

    # Classification (Step 2)
    category: Mapped[str] = mapped_column(String(50))
    urgency: Mapped[str] = mapped_column(String(20))
    sentiment: Mapped[str] = mapped_column(String(20))
    auto_resolve_eligible: Mapped[bool] = mapped_column(Boolean)
    classification_reasoning: Mapped[str] = mapped_column(Text)

    # Retrieval + drafting (Step 3-4)
    kb_chunks_used: Mapped[list | None] = mapped_column(JSON, nullable=True)
    draft_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Confidence scoring (Step 5)
    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Escalation (Step 6)
    escalation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_next_step: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Final routing decision
    final_action: Mapped[str] = mapped_column(String(30))

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return (
            f"<TicketRecord id={self.id} subject={self.subject[:30]!r} "
            f"final_action={self.final_action}>"
        )
