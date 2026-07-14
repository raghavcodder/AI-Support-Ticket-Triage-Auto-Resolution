"""
customer-facing "TaskFlow" website with a floating chat widget,
powered by the same pipeline and database as the internal dashboard.

"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.resolve import process_ticket
from app.db.database import init_db
from app.db.crud import save_ticket_record

st.set_page_config(page_title="TaskFlow", page_icon="✅", layout="wide")
init_db()

# ---------------------------------------------------------------------
# Global styling -- hide Streamlit chrome, apply a marketing-site look
# ---------------------------------------------------------------------
st.markdown("""
<style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 2rem; max-width: 1100px;}

    .tf-navbar {
        display: flex; justify-content: space-between; align-items: center;
        padding: 16px 0; border-bottom: 1px solid #eaeaf0; margin-bottom: 40px;
    }
    .tf-logo {font-size: 22px; font-weight: 700; color: #1a1a2e;}
    .tf-navlinks {display: flex; gap: 28px; color: #555; font-size: 15px;}

    .tf-hero {text-align: center; padding: 40px 0 60px 0;}
    .tf-hero h1 {font-size: 42px; color: #1a1a2e; margin-bottom: 12px;}
    .tf-hero p {font-size: 18px; color: #666; max-width: 560px; margin: 0 auto 28px auto;}

    .tf-cta {
        display: inline-block; background: #4a4a8a; color: white !important;
        padding: 12px 28px; border-radius: 8px; font-weight: 600;
        text-decoration: none; font-size: 15px;
    }

    .tf-feature-card {
        background: #f9f9fc; border-radius: 12px; padding: 24px;
        height: 100%; border: 1px solid #eaeaf0;
    }
    .tf-feature-card h3 {color: #1a1a2e; font-size: 17px; margin-bottom: 8px;}
    .tf-feature-card p {color: #666; font-size: 14px; line-height: 1.5;}

    /* Floating chat bubble button -- targets the container immediately
       following the #chat-toggle-anchor marker div. This relies on
       Streamlit rendering each element in its own wrapper div in DOM
       order; if a future Streamlit version changes that structure, this
       selector may need adjusting. */
    #chat-toggle-anchor + div {
        position: fixed !important; bottom: 24px; right: 24px; z-index: 999999;
    }
    #chat-toggle-anchor + div button {
        border-radius: 50% !important; width: 62px !important; height: 62px !important;
        font-size: 26px !important; background: #4a4a8a !important; color: white !important;
        border: none !important; box-shadow: 0 6px 18px rgba(0,0,0,0.25) !important;
    }

    /* Floating chat panel */
    #chat-panel-anchor + div {
        position: fixed !important; bottom: 100px; right: 24px; z-index: 999998;
        width: 380px; max-height: 65vh; overflow-y: auto;
        background: white; border-radius: 16px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.22); padding: 18px;
        border: 1px solid #eaeaf0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# Marketing site content (fake -- just gives the chat widget a home)
# ---------------------------------------------------------------------
st.markdown("""
<div class="tf-navbar">
    <div class="tf-logo">✅ TaskFlow</div>
    <div class="tf-navlinks">
        <span>Product</span><span>Pricing</span><span>Docs</span><span>Login</span>
    </div>
</div>
<div class="tf-hero">
    <h1>Project management that keeps up with you</h1>
    <p>Boards, automations, and integrations for teams who'd rather ship
    than manage spreadsheets.</p>
    <a class="tf-cta" href="#">Start free trial</a>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
features = [
    ("⚡", "Automations", "Connect Zapier, Slack, and your API to keep every board in sync automatically."),
    ("🔒", "Enterprise-ready", "Two-factor auth, granular permissions, and full data export whenever you need it."),
    ("📊", "Real-time boards", "See exactly where every project stands, updated the moment anything changes."),
]
for col, (icon, title, desc) in zip([col1, col2, col3], features):
    with col:
        st.markdown(f"""
        <div class="tf-feature-card">
            <h3>{icon} {title}</h3>
            <p>{desc}</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='height: 400px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# Chat widget state
# ---------------------------------------------------------------------
if "chat_open" not in st.session_state:
    st.session_state.chat_open = False
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hi! I'm the TaskFlow support assistant. Ask me anything "
            "about your account, billing, or the product.",
        }
    ]

# ---------------------------------------------------------------------
# Floating toggle button
# ---------------------------------------------------------------------
st.markdown('<div id="chat-toggle-anchor"></div>', unsafe_allow_html=True)
with st.container():
    icon = "✕" if st.session_state.chat_open else "💬"
    if st.button(icon, key="toggle_chat_btn"):
        st.session_state.chat_open = not st.session_state.chat_open
        st.rerun()

# ---------------------------------------------------------------------
# Floating chat panel (only rendered when open)
# ---------------------------------------------------------------------
if st.session_state.chat_open:
    st.markdown('<div id="chat-panel-anchor"></div>', unsafe_allow_html=True)
    with st.container():
        st.markdown("**TaskFlow Support** 🟢 *typically replies instantly*")
        st.divider()

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_input(
                "Message", placeholder="Type your question...", label_visibility="collapsed"
            )
            sent = st.form_submit_button("Send", use_container_width=True)

        if sent and user_input.strip():
            st.session_state.messages.append({"role": "user", "content": user_input})

            with st.spinner("Support assistant is typing..."):
                # Treat the chat message as a ticket: a short subject
                # derived from the message, and the full text as the body.
                subject = user_input if len(user_input) <= 60 else user_input[:57] + "..."
                result = process_ticket(subject, user_input)
                record = save_ticket_record(subject, user_input, result)

            # Customer-facing reply -- deliberately strips out everything
            # internal (confidence, reasoning, escalation summary). The
            # customer only ever sees the answer or a "we've got it" note.
            if result["final_action"] == "auto_send":
                reply = result["draft_response"]
            else:
                reply = (
                    f"Thanks for reaching out! I've forwarded this to our "
                    f"support team (ticket #{record.id}) and someone will "
                    f"follow up with you shortly. Is there anything else "
                    f"I can help with in the meantime?"
                )

            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()
