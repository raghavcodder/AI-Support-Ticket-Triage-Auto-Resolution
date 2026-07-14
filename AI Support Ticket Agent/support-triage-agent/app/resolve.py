"""classify -> retrieve -> draft -> score confidence -> escalation
summary -> persist to MySQL
"""

import os
import sys
from pathlib import Path

# Make sure the project root (the folder containing app/) is on sys.path,
# regardless of how this script is invoked -- running it via a full path
# (e.g. from VSCode's "Run Python File") only adds this file's own folder
# to sys.path by default, which breaks "from app.X import Y" imports below.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from app.classify import classify_ticket
from app.rag.retriever import retrieve
from app.prompts.resolve_prompt import RESOLVE_SYSTEM_PROMPT, RESOLVE_USER_TEMPLATE
from app.prompts.confidence_prompt import CONFIDENCE_SYSTEM_PROMPT, CONFIDENCE_USER_TEMPLATE
from app.prompts.escalation_prompt import ESCALATION_SYSTEM_PROMPT, ESCALATION_USER_TEMPLATE
from app.schemas import ConfidenceAssessment, EscalationSummary
from app.rate_limit import paced_call
from app.db.database import init_db
from app.db.crud import save_ticket_record

load_dotenv()

# Below this confidence score, a draft is escalated with the draft attached
# as a suggestion rather than auto-sent. Tune this based on eval results --
# lower it once you trust the resolve_prompt more, or if false-escalations
# (good drafts sent to review unnecessarily) start costing too much human time.
CONFIDENCE_THRESHOLD = 75

llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0.3)

resolve_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", RESOLVE_SYSTEM_PROMPT),
        ("user", RESOLVE_USER_TEMPLATE),
    ]
)
resolve_chain = resolve_prompt | llm

# Confidence scoring uses temperature=0 (unlike drafting) -- we want
# consistent, repeatable judgments here, not creative variation.
confidence_llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
confidence_structured_llm = confidence_llm.with_structured_output(ConfidenceAssessment)

confidence_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", CONFIDENCE_SYSTEM_PROMPT),
        ("user", CONFIDENCE_USER_TEMPLATE),
    ]
)
confidence_chain = confidence_prompt | confidence_structured_llm

# Escalation summaries use the same low-temperature pattern as confidence
# scoring -- this is a factual triage summary, not creative writing.
escalation_llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
escalation_structured_llm = escalation_llm.with_structured_output(EscalationSummary)

escalation_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", ESCALATION_SYSTEM_PROMPT),
        ("user", ESCALATION_USER_TEMPLATE),
    ]
)
escalation_chain = escalation_prompt | escalation_structured_llm


def format_kb_context(chunks: list[dict]) -> str:
    """Turn retrieved chunks into a labeled block the LLM can cite from."""
    if not chunks:
        return "(no relevant knowledge base excerpts found)"

    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[Excerpt {i} - source: {chunk['source']}, section: {chunk['section']}]\n"
            f"{chunk['content']}"
        )
    return "\n\n".join(parts)


def draft_response(subject: str, body: str, kb_chunks: list[dict]) -> str:
    """Draft a grounded response given a ticket and retrieved KB chunks."""
    kb_context = format_kb_context(kb_chunks)
    result = paced_call(
        resolve_chain.invoke,
        {"subject": subject, "body": body, "kb_context": kb_context},
    )
    return result.content


def score_confidence(
    subject: str, body: str, kb_chunks: list[dict], draft: str
) -> ConfidenceAssessment:
    """
    Step 5: rate how confident we should be that `draft` can be sent as-is.
    This is a separate LLM call from drafting -- a model reviewing its own
    (or another's) output with fresh eyes catches things a single combined
    "draft and rate yourself" call tends to rubber-stamp.
    """
    kb_context = format_kb_context(kb_chunks)
    return paced_call(
        confidence_chain.invoke,
        {
            "subject": subject,
            "body": body,
            "kb_context": kb_context,
            "draft_response": draft,
        },
    )


def generate_escalation_summary(
    subject: str, body: str, classification, has_draft: bool
) -> EscalationSummary:
    """
    Step 6: produce a triage-ready summary for a human agent, for tickets
    that are escalated either because they were never auto-resolve-eligible,
    or because a draft existed but confidence scoring flagged it for review.
    """
    return paced_call(
        escalation_chain.invoke,
        {
            "subject": subject,
            "body": body,
            "category": classification.category,
            "urgency": classification.urgency,
            "sentiment": classification.sentiment,
            "classification_reasoning": classification.reasoning,
            "has_draft": has_draft,
        },
    )


def process_ticket(subject: str, body: str) -> dict:
    """
    Full pipeline for one ticket: classify -> (if eligible) retrieve ->
    draft -> score confidence -> route to auto-send or escalate (with a
    real triage summary for the human queue).
    Returns a dict describing what happened at each stage, so you can
    inspect the reasoning, not just the final answer.
    """
    classification = classify_ticket(subject, body)

    result = {
        "subject": subject,
        "category": classification.category,
        "urgency": classification.urgency,
        "sentiment": classification.sentiment,
        "auto_resolve_eligible": classification.auto_resolve_eligible,
        "classification_reasoning": classification.reasoning,
        "kb_chunks_used": [],
        "draft_response": None,
        "confidence_score": None,
        "confidence_reasoning": None,
        "final_action": None,
        "escalation_summary": None,
        "recommended_next_step": None,
    }

    if not classification.auto_resolve_eligible:
        result["final_action"] = "escalate_no_draft"
        summary = generate_escalation_summary(
            subject, body, classification, has_draft=False
        )
        result["escalation_summary"] = summary.summary
        result["recommended_next_step"] = summary.recommended_next_step
        return result

    # Retrieve using subject+body together -- gives the retriever more
    # signal than the subject alone.
    query = f"{subject}. {body}"
    kb_chunks = retrieve(query, k=3)
    result["kb_chunks_used"] = [
        f"{c['source']} ({c['section']})" for c in kb_chunks
    ]

    draft = draft_response(subject, body, kb_chunks)
    result["draft_response"] = draft

    confidence = score_confidence(subject, body, kb_chunks, draft)
    result["confidence_score"] = confidence.confidence_score
    result["confidence_reasoning"] = confidence.reasoning

    if confidence.confidence_score >= CONFIDENCE_THRESHOLD:
        result["final_action"] = "auto_send"
    else:
        result["final_action"] = "escalate_with_draft"
        summary = generate_escalation_summary(
            subject, body, classification, has_draft=True
        )
        result["escalation_summary"] = summary.summary
        result["recommended_next_step"] = summary.recommended_next_step

    return result


if __name__ == "__main__":
    import pandas as pd

    print("Initializing database (creating it and tables if they don't exist)...")
    init_db()

    tickets_path = os.path.join(PROJECT_ROOT, "data", "sample_tickets.csv")
    df = pd.read_csv(tickets_path)

    # Now running the full 20-ticket set for real eval numbers -- Groq's
    # free tier has enough headroom that this isn't a concern anymore.
    # Drop back to df.head(N) if you want a quicker spot-check instead.
    sample = df

    print(f"Running full pipeline on {len(sample)} tickets "
          f"(confidence threshold={CONFIDENCE_THRESHOLD})...\n")

    action_counts = {"auto_send": 0, "escalate_with_draft": 0, "escalate_no_draft": 0}

    for _, row in sample.iterrows():
        print(f"{'=' * 70}")
        print(f"Ticket: {row['subject']}")
        result = process_ticket(row["subject"], row["body"])
        action_counts[result["final_action"]] += 1

        record = save_ticket_record(row["subject"], row["body"], result)
        print(f"  [saved to DB as ticket_records.id={record.id}]")

        print(f"  category={result['category']} | urgency={result['urgency']} "
              f"| auto_resolve_eligible={result['auto_resolve_eligible']}")
        print(f"  classification reasoning: {result['classification_reasoning']}")

        if result["final_action"] == "escalate_no_draft":
            print(f"\n  → ESCALATE (no draft attempted)")
            print(f"  Queue summary: {result['escalation_summary']}")
            print(f"  Recommended next step: {result['recommended_next_step']}\n")
        else:
            print(f"  KB chunks used: {result['kb_chunks_used']}")
            print(f"  confidence={result['confidence_score']} "
                  f"| confidence reasoning: {result['confidence_reasoning']}")

            if result["final_action"] == "auto_send":
                print(f"  → AUTO-SEND")
                print(f"\n  DRAFT RESPONSE:\n  {result['draft_response']}\n")
            else:
                print(f"  → ESCALATE (draft attached as suggestion)")
                print(f"  Queue summary: {result['escalation_summary']}")
                print(f"  Recommended next step: {result['recommended_next_step']}")
                print(f"\n  DRAFT (for agent review):\n  {result['draft_response']}\n")

    print(f"{'=' * 70}")
    print(f"Summary: {action_counts}")
