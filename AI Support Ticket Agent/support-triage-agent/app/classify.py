import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from app.schemas import TicketClassification
from app.prompts.classify_prompt import CLASSIFY_SYSTEM_PROMPT, CLASSIFY_USER_TEMPLATE
from app.rate_limit import paced_call

load_dotenv()

llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
structured_llm = llm.with_structured_output(TicketClassification)

classify_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", CLASSIFY_SYSTEM_PROMPT),
        ("user", CLASSIFY_USER_TEMPLATE),
    ]
)

classify_chain = classify_prompt | structured_llm


def classify_ticket(subject: str, body: str) -> TicketClassification:
    """Classify a single ticket. This is the function later steps will call."""
    return paced_call(
        classify_chain.invoke, {"subject": subject, "body": body}
    )


if __name__ == "__main__":
    import pandas as pd

    tickets_path = os.path.join(PROJECT_ROOT, "data", "sample_tickets.csv")
    df = pd.read_csv(tickets_path)

    print(f"Classifying {len(df)} sample tickets "
          f"(paced for free tier)...\n")

    results = []

    for _, row in df.iterrows():
        result = classify_ticket(row["subject"], row["body"])

        results.append(
            {
                "ticket_id": row["ticket_id"],
                "subject": row["subject"],
                "predicted_category": result.category,
                "expected_category": row.get("expected_category", "?"),
                "urgency": result.urgency,
                "sentiment": result.sentiment,
                "auto_resolve_eligible": result.auto_resolve_eligible,
                "reasoning": result.reasoning,
            }
        )
        match = "✓" if result.category == row.get("expected_category") else "✗"
        print(f"[{match}] {row['ticket_id']}: {row['subject'][:50]}")
        print(f"      predicted={result.category} | expected={row.get('expected_category', '?')} "
              f"| urgency={result.urgency} | auto_resolve={result.auto_resolve_eligible}")
        print(f"      reasoning: {result.reasoning}\n")

    results_df = pd.DataFrame(results)
    results_path = os.path.join(PROJECT_ROOT, "data", "classification_results.csv")
    results_df.to_csv(results_path, index=False)

    if "expected_category" in df.columns:
        accuracy = (results_df["predicted_category"] == results_df["expected_category"]).mean()
        print(f"\nClassification accuracy vs hand-labeled ground truth: {accuracy:.1%}")

    print(f"\nFull results saved to {results_path}")
