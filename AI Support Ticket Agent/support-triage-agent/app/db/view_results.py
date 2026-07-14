import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select, func
from app.db.database import get_session
from app.db.models import TicketRecord


def main():
    session = get_session()
    try:
        records = session.execute(select(TicketRecord)).scalars().all()

        if not records:
            print("No records found yet -- run `python app/resolve.py` first.")
            return

        print(f"Total tickets processed: {len(records)}\n")

        # Breakdown by final action
        action_counts = {}
        for r in records:
            action_counts[r.final_action] = action_counts.get(r.final_action, 0) + 1
        print("By final action:")
        for action, count in sorted(action_counts.items()):
            pct = count / len(records) * 100
            print(f"  {action}: {count} ({pct:.0f}%)")

        # Breakdown by category
        category_counts = {}
        for r in records:
            category_counts[r.category] = category_counts.get(r.category, 0) + 1
        print("\nBy category:")
        for category, count in sorted(category_counts.items()):
            print(f"  {category}: {count}")

        # Average confidence score, where scored
        scored = [r.confidence_score for r in records if r.confidence_score is not None]
        if scored:
            avg_confidence = sum(scored) / len(scored)
            print(f"\nAverage confidence score (where scored): {avg_confidence:.1f}")
            print(f"Tickets scored: {len(scored)} / {len(records)}")

        # Most recent 5, for a quick sanity check
        print("\nMost recent 5 tickets:")
        recent = sorted(records, key=lambda r: r.created_at, reverse=True)[:5]
        for r in recent:
            print(f"  [{r.created_at}] {r.subject[:50]:50s} -> {r.final_action}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
