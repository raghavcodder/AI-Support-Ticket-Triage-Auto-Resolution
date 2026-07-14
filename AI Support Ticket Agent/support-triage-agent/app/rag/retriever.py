import os
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PERSIST_DIR = os.path.join(PROJECT_ROOT, "chroma_db")
COLLECTION_NAME = "support_kb"

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

_vectorstore = None


def get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        if not os.path.exists(PERSIST_DIR):
            raise FileNotFoundError(
                f"No vector store found at {PERSIST_DIR}/. "
                "Run `python app/rag/ingest.py` first."
            )
        _vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=PERSIST_DIR,
        )
    return _vectorstore


def retrieve(query: str, k: int = 3) -> list[dict]:
    """
    Retrieve the top-k most relevant KB chunks for a query.
    Returns a list of dicts with content, source, and similarity score
    so callers can inspect what was actually used.
    """
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search_with_relevance_scores(query, k=k)

    return [
        {
            "content": doc.page_content,
            "source": doc.metadata.get("source", "unknown"),
            "section": doc.metadata.get("section", ""),
            "relevance_score": round(score, 3),
        }
        for doc, score in results
    ]


if __name__ == "__main__":
    # Test queries mirroring real tickets from data/sample_tickets.csv --
    # check each one pulls back the doc you'd expect a human to point to.
    test_queries = [
        ("T001 - refund for accidental annual upgrade",
         "I meant to renew monthly but got charged for annual instead, can I get a refund?"),
        ("T004 - Zapier integration stopped syncing",
         "Our Zapier automation stopped working, no error message"),
        ("T005 - how to add a team member",
         "How do I invite a new person to my workspace?"),
        ("T009 - API rate limits",
         "What are the API rate limits for the Business plan?"),
        ("T013 - permissions not saving",
         "Permission settings revert back to full edit access after a few minutes"),
    ]

    for label, query in test_queries:
        print(f"\n=== {label} ===")
        print(f"Query: {query}")
        results = retrieve(query, k=2)
        for i, r in enumerate(results, 1):
            print(f"  [{i}] source={r['source']} | score={r['relevance_score']}")
            print(f"      section: {r['section']}")
            print(f"      preview: {r['content'][:150]}...")
