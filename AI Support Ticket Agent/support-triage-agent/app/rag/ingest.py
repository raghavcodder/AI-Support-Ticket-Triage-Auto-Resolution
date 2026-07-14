import os
import glob
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from pypdf import PdfReader

load_dotenv()

# Resolve paths relative to the project root (two levels up from this file:
# app/rag/ingest.py -> app/ -> project root), so this works no matter what
# directory you run the script from.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KB_DIR = os.path.join(PROJECT_ROOT, "data", "knowledge_base")
PERSIST_DIR = os.path.join(PROJECT_ROOT, "chroma_db")
COLLECTION_NAME = "support_kb"

# Gemini's embedding model - separate rate limit from the chat model,
# but still free tier, so keep this in mind if you add many more docs.
# Note: text-embedding-004 was deprecated Jan 2026 -- gemini-embedding-001
# is the current production replacement.
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

# Split on markdown headers first (keeps each KB section coherent), then
# fall back to character splitting for anything still too long.
header_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("##", "section")]
)
char_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)


def load_markdown_chunks() -> list[Document]:
    chunks = []
    for filepath in glob.glob(f"{KB_DIR}/*.md"):
        with open(filepath, "r") as f:
            text = f.read()

        source_name = os.path.basename(filepath)
        header_chunks = header_splitter.split_text(text)

        for chunk in header_chunks:
            chunk.metadata["source"] = source_name
            # Further split only if a section is unusually long
            if len(chunk.page_content) > 500:
                sub_chunks = char_splitter.split_documents([chunk])
                chunks.extend(sub_chunks)
            else:
                chunks.append(chunk)

    return chunks


def load_pdf_chunks() -> list[Document]:
    """
    PDFs don't have markdown headers to split on, so we extract text
    per page and chunk with the character splitter instead. Each chunk
    keeps its source filename and page number in metadata, so retrieval
    results can point back to exactly where the answer came from.
    """
    chunks = []
    for filepath in glob.glob(f"{KB_DIR}/*.pdf"):
        source_name = os.path.basename(filepath)
        reader = PdfReader(filepath)

        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text()
            if not page_text or not page_text.strip():
                continue

            page_doc = Document(
                page_content=page_text,
                metadata={"source": source_name, "page": page_num},
            )
            sub_chunks = char_splitter.split_documents([page_doc])
            chunks.extend(sub_chunks)

    return chunks


def load_and_chunk_docs() -> list[Document]:
    return load_markdown_chunks() + load_pdf_chunks()


def build_vectorstore():
    chunks = load_and_chunk_docs()
    print(f"Loaded {len(chunks)} chunks from {KB_DIR} (.md + .pdf)")

    if not chunks:
        raise FileNotFoundError(
            f"No .md or .pdf files found in {KB_DIR}. Check that the "
            "knowledge_base folder exists and contains documents at that path."
        )

    # Rebuild the collection from scratch each time, rather than appending --
    # otherwise re-running this after editing a doc leaves stale duplicate
    # chunks from the old version alongside the new ones.
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=PERSIST_DIR,
    )
    existing_ids = vectorstore.get()["ids"]
    if existing_ids:
        vectorstore.delete(ids=existing_ids)
        print(f"Cleared {len(existing_ids)} existing chunks before rebuilding")

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=PERSIST_DIR,
    )
    print(f"Vector store persisted to {PERSIST_DIR}/")
    return vectorstore


if __name__ == "__main__":
    build_vectorstore()

