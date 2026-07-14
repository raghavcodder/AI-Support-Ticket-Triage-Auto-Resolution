"""
Streamlit dashboard for the support triage agent.

Three tabs:
- Submit Ticket: run a ticket through the live pipeline and see every stage
- Escalation Queue: everything currently waiting on a human, pulled from MySQL
- Analytics: aggregate stats across all persisted tickets
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
from sqlalchemy import select

from app.resolve import process_ticket
from app.db.database import init_db, get_session
from app.db.models import TicketRecord
from app.db.crud import save_ticket_record

st.set_page_config(page_title="Support Triage Agent", page_icon="🎫", layout="wide")

# Safe to call on every load -- creates the DB/tables only if missing.
init_db()

st.title("🎫 AI Support Ticket Triage Agent")
st.caption(
    "LangChain-powered classification, RAG-grounded resolution, and "
    "confidence-based routing for TaskFlow support tickets."
)

tab_submit, tab_queue, tab_analytics = st.tabs(
    ["📥 Submit Ticket", "🚨 Escalation Queue", "📊 Analytics"]
)

# ---------------------------------------------------------------------
# TAB 1: Submit a ticket and watch the pipeline run live
# ---------------------------------------------------------------------
with tab_submit:
    st.subheader("Submit a new ticket")

    with st.form("ticket_form"):
        subject = st.text_input("Subject", placeholder="e.g. Can't log in to my account")
        body = st.text_area(
            "Body",
            placeholder="Describe the issue as the customer would write it...",
            height=120,
        )
        submitted = st.form_submit_button("Process Ticket", type="primary")

    if submitted:
        if not subject or not body:
            st.error("Please fill in both subject and body.")
        else:
            with st.spinner("Running pipeline: classify → retrieve → draft → score → route..."):
                result = process_ticket(subject, body)
                record = save_ticket_record(subject, body, result)

            st.success(f"Processed and saved as ticket #{record.id}")

            col1, col2, col3 = st.columns(3)
            col1.metric("Category", result["category"])
            col2.metric("Urgency", result["urgency"].upper())
            col3.metric("Sentiment", result["sentiment"])

            st.markdown(f"**Classification reasoning:** {result['classification_reasoning']}")
            st.divider()

            action = result["final_action"]

            if action == "escalate_no_draft":
                st.warning("🚨 Escalated — not auto-resolve eligible, no draft attempted")
                st.markdown(f"**Queue summary:** {result['escalation_summary']}")
                st.markdown(f"**Recommended next step:** {result['recommended_next_step']}")

            else:
                st.markdown(f"**KB chunks used:** {', '.join(result['kb_chunks_used'])}")
                st.markdown(
                    f"**Confidence:** {result['confidence_score']}/100 — "
                    f"{result['confidence_reasoning']}"
                )

                if action == "auto_send":
                    st.success("✅ Auto-sent to customer")
                else:
                    st.warning("🚨 Escalated — draft attached for human review")
                    st.markdown(f"**Queue summary:** {result['escalation_summary']}")
                    st.markdown(f"**Recommended next step:** {result['recommended_next_step']}")

                st.text_area(
                    "Draft response", result["draft_response"], height=150, disabled=True
                )

# ---------------------------------------------------------------------
# TAB 2: Escalation queue -- everything that needs a human, newest first
# ---------------------------------------------------------------------
with tab_queue:
    st.subheader("Escalation queue")

    session = get_session()
    try:
        records = (
            session.execute(
                select(TicketRecord)
                .where(TicketRecord.final_action != "auto_send")
                .order_by(TicketRecord.created_at.desc())
            )
            .scalars()
            .all()
        )
    finally:
        session.close()

    if not records:
        st.info("No escalated tickets yet — process some in the Submit tab first.")
    else:
        urgency_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}

        for r in records:
            icon = urgency_icon.get(r.urgency, "⚪")
            label = f"{icon} [{r.urgency.upper()}] {r.subject} — {r.final_action}"

            with st.expander(label):
                col1, col2 = st.columns(2)
                col1.markdown(f"**Category:** {r.category}")
                col2.markdown(f"**Sentiment:** {r.sentiment}")

                st.markdown(f"**Summary:** {r.escalation_summary}")
                st.markdown(f"**Recommended next step:** {r.recommended_next_step}")

                if r.draft_response:
                    st.text_area(
                        "Draft (for agent review)",
                        r.draft_response,
                        height=100,
                        key=f"draft_{r.id}",
                        disabled=True,
                    )

# ---------------------------------------------------------------------
# TAB 3: Aggregate analytics across everything persisted
# ---------------------------------------------------------------------
with tab_analytics:
    st.subheader("Analytics")

    session = get_session()
    try:
        records = session.execute(select(TicketRecord)).scalars().all()
    finally:
        session.close()

    if not records:
        st.info("No data yet — process some tickets in the Submit tab first.")
    else:
        df = pd.DataFrame(
            [
                {
                    "final_action": r.final_action,
                    "category": r.category,
                    "urgency": r.urgency,
                    "confidence_score": r.confidence_score,
                }
                for r in records
            ]
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("Total tickets", len(df))

        auto_rate = (df["final_action"] == "auto_send").mean() * 100
        col2.metric("Auto-resolve rate", f"{auto_rate:.0f}%")

        scored = df["confidence_score"].dropna()
        avg_conf = scored.mean() if not scored.empty else None
        col3.metric("Avg confidence (scored)", f"{avg_conf:.0f}" if avg_conf else "N/A")

        st.divider()

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**By final action**")
            st.bar_chart(df["final_action"].value_counts())
        with col_b:
            st.markdown("**By category**")
            st.bar_chart(df["category"].value_counts())

        if not scored.empty:
            st.markdown("**Confidence score distribution (scored tickets only)**")
            st.bar_chart(scored.value_counts().sort_index())
