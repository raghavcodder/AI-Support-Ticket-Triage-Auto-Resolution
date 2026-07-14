"""
Generates the two official-looking PDF knowledge base documents for
TaskFlow, replacing/supplementing the plain markdown KB docs.

Run once to (re)generate:
    python scripts/generate_kb_pdfs.py

The factual content matches what's already in data/knowledge_base/*.md,
just expanded and formatted as real documents -- so existing eval
tickets (refund policy, rate limits, etc.) stay valid against the richer
PDF versions.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, Table, TableStyle
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "knowledge_base")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="DocTitle", parent=styles["Title"], fontSize=22, spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="DocSubtitle", parent=styles["Normal"], fontSize=11,
    textColor=colors.HexColor("#666666"), spaceAfter=24,
))
styles.add(ParagraphStyle(
    name="SectionHeading", parent=styles["Heading1"], fontSize=15,
    spaceBefore=20, spaceAfter=8, textColor=colors.HexColor("#1a1a2e"),
))
styles.add(ParagraphStyle(
    name="SubHeading", parent=styles["Heading2"], fontSize=12,
    spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#333355"),
))
body_style = styles["Normal"]
body_style.spaceAfter = 8
body_style.leading = 15


def bullet_list(items):
    return ListFlowable(
        [ListItem(Paragraph(item, body_style), bulletColor=colors.HexColor("#4a4a8a"))
         for item in items],
        bulletType="bullet",
        leftIndent=18,
    )


def build_billing_pdf():
    path = os.path.join(OUTPUT_DIR, "TaskFlow_Billing_and_Terms.pdf")
    doc = SimpleDocTemplate(
        path, pagesize=letter,
        topMargin=0.9 * inch, bottomMargin=0.9 * inch,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
    )
    story = []

    story.append(Paragraph("TaskFlow Billing &amp; Terms", styles["DocTitle"]))
    story.append(Paragraph(
        "Official billing policy, refund terms, and invoicing reference. "
        "Effective for all TaskFlow subscription plans.",
        styles["DocSubtitle"],
    ))

    story.append(Paragraph("1. Plan Changes", styles["SectionHeading"]))
    story.append(Paragraph(
        "Users can switch between monthly and annual billing at any time "
        "from Settings &gt; Billing &gt; Plan. Plan changes take effect "
        "immediately, with charges prorated for the remainder of the "
        "current billing period.",
        body_style,
    ))

    story.append(Paragraph("2. Refund Policy", styles["SectionHeading"]))
    story.append(bullet_list([
        "<b>Accidental duplicate charges:</b> always eligible for a full refund, "
        "processed within 3-5 business days.",
        "<b>Accidental plan upgrades:</b> eligible for reversal and refund of the "
        "difference within 7 days of the charge.",
        "<b>Standard subscription cancellations:</b> no refund for the current "
        "billing period, but access continues until the period ends.",
    ]))

    story.append(Paragraph("3. Invoices &amp; Billing History", styles["SectionHeading"]))
    story.append(Paragraph(
        "All invoices are available under Settings &gt; Billing &gt; Invoice "
        "History. Invoices are generated automatically on the billing date "
        "each month or year, and are available as PDF downloads going back "
        "<b>24 months</b>.",
        body_style,
    ))

    story.append(Paragraph("4. Price Changes", styles["SectionHeading"]))
    story.append(Paragraph(
        "Existing customers are notified via email at least 30 days before "
        "any price change takes effect. Customers may cancel or lock in "
        "their current rate by switching to annual billing before the "
        "change date.",
        body_style,
    ))

    story.append(Paragraph("5. Payment Methods", styles["SectionHeading"]))
    story.append(Paragraph(
        "TaskFlow accepts major credit and debit cards (Visa, Mastercard, "
        "American Express) as well as ACH bank transfer for annual Business "
        "plan subscriptions. Payment method can be updated at any time "
        "under Settings &gt; Billing &gt; Payment Method.",
        body_style,
    ))

    story.append(Paragraph("6. Taxes", styles["SectionHeading"]))
    story.append(Paragraph(
        "Applicable sales tax or VAT is calculated automatically based on "
        "the billing address on file and shown as a separate line item on "
        "every invoice.",
        body_style,
    ))

    plan_data = [
        ["Plan", "API Rate Limit", "Support"],
        ["Free", "100 requests/hour", "Community forum"],
        ["Pro", "1,000 requests/hour", "Email, 24h response"],
        ["Business", "10,000 requests/hour", "Priority email + chat"],
    ]
    table = Table(plan_data, colWidths=[1.7 * inch, 2.2 * inch, 2.2 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f7")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(Paragraph("7. Plan Comparison Reference", styles["SectionHeading"]))
    story.append(table)

    doc.build(story)
    print(f"Created {path}")


def build_product_guide_pdf():
    path = os.path.join(OUTPUT_DIR, "TaskFlow_Product_and_Integrations_Guide.pdf")
    doc = SimpleDocTemplate(
        path, pagesize=letter,
        topMargin=0.9 * inch, bottomMargin=0.9 * inch,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
    )
    story = []

    story.append(Paragraph("TaskFlow Product &amp; Integrations Guide", styles["DocTitle"]))
    story.append(Paragraph(
        "Account management, security, data handling, and third-party "
        "integration reference for TaskFlow workspaces.",
        styles["DocSubtitle"],
    ))

    story.append(Paragraph("1. Account &amp; Team Management", styles["SectionHeading"]))

    story.append(Paragraph("1.1 Adding Team Members", styles["SubHeading"]))
    story.append(Paragraph(
        "Go to Settings &gt; Team &gt; Invite Member, enter their email, and "
        "select a role (Admin, Editor, or Viewer). They'll receive an email "
        "invite that expires after 7 days.",
        body_style,
    ))

    story.append(Paragraph("1.2 Permissions", styles["SubHeading"]))
    story.append(Paragraph(
        "Board-level permissions can be set per member under Board Settings "
        "&gt; Permissions. Permission changes can take up to 2 minutes to "
        "propagate; if a permission reverts immediately, this is a known "
        "sync issue currently being tracked by engineering and should be "
        "escalated rather than treated as user error.",
        body_style,
    ))

    story.append(Paragraph("1.3 Two-Factor Authentication", styles["SubHeading"]))
    story.append(Paragraph(
        "Enable 2FA under Settings &gt; Security &gt; Two-Factor "
        "Authentication. Supports authenticator apps (Google Authenticator, "
        "Authy) via QR code setup.",
        body_style,
    ))

    story.append(Paragraph("1.4 Data Export", styles["SubHeading"]))
    story.append(Paragraph(
        "Full workspace export (all boards, all data) is available under "
        "Settings &gt; Data &gt; Export Workspace, in CSV or JSON format. "
        "Exports remain available for 30 days after account cancellation "
        "before data is permanently deleted.",
        body_style,
    ))

    story.append(Paragraph("1.5 Password Reset Issues", styles["SubHeading"]))
    story.append(Paragraph(
        "If a password reset link isn't working, first check for multiple "
        "reset emails, since only the most recent link is valid. If login "
        "still fails after using the newest link, this may indicate an "
        "account lockout from repeated failed attempts, which requires "
        "escalation to support for a manual unlock.",
        body_style,
    ))

    story.append(Paragraph("2. Integrations Troubleshooting", styles["SectionHeading"]))

    story.append(Paragraph("2.1 Zapier", styles["SubHeading"]))
    story.append(Paragraph(
        "If Zapier automations stop syncing without an error, the most "
        "common cause is an expired OAuth token. Reconnect the integration "
        "under Settings &gt; Integrations &gt; Zapier &gt; Reconnect, which "
        "resolves the issue in most cases.",
        body_style,
    ))

    story.append(Paragraph("2.2 Slack Notifications", styles["SubHeading"]))
    story.append(Paragraph(
        "If Slack notifications stop arriving, check Settings &gt; "
        "Integrations &gt; Slack to confirm the connection is still "
        "active, since Slack tokens can expire after workspace admin "
        "changes on Slack's side. Reconnecting resolves this in most "
        "cases; if not, the issue may be on Slack's delivery side and "
        "should be escalated.",
        body_style,
    ))

    story.append(Paragraph("2.3 API Rate Limits", styles["SubHeading"]))
    story.append(bullet_list([
        "Free plan: 100 requests/hour",
        "Pro plan: 1,000 requests/hour",
        "Business plan: 10,000 requests/hour",
    ]))
    story.append(Paragraph(
        "Rate limit headers are included in every API response "
        "(X-RateLimit-Remaining) so usage can be monitored in real time.",
        body_style,
    ))

    doc.build(story)
    print(f"Created {path}")


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    build_billing_pdf()
    build_product_guide_pdf()
