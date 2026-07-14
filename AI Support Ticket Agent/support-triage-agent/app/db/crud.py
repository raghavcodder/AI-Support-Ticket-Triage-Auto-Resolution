"""
Save a process_ticket() result dict into the database.
Kept as one function so resolve.py doesn't need to know anything about
SQLAlchemy sessions.
"""

from app.db.database import get_session
from app.db.models import TicketRecord


def save_ticket_record(subject: str, body: str, result: dict) -> TicketRecord:
    """
    Persist one ticket's full pipeline result. Called once per ticket
    after process_ticket() finishes, regardless of which path it took
    (auto_send / escalate_with_draft / escalate_no_draft).
    """
    session = get_session()
    try:
        record = TicketRecord(
            subject=subject,
            body=body,
            category=result["category"],
            urgency=result["urgency"],
            sentiment=result["sentiment"],
            auto_resolve_eligible=result["auto_resolve_eligible"],
            classification_reasoning=result["classification_reasoning"],
            kb_chunks_used=result["kb_chunks_used"] or None,
            draft_response=result["draft_response"],
            confidence_score=result["confidence_score"],
            confidence_reasoning=result["confidence_reasoning"],
            escalation_summary=result["escalation_summary"],
            recommended_next_step=result["recommended_next_step"],
            final_action=result["final_action"],
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record
    finally:
        session.close()
