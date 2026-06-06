"""
app/core/rag_pipeline.py
────────────────────────
LangChain RAG pipeline using Groq (Llama 3.1) as the LLM.

The chain is built fresh per request using the client's FAISS index.
We do NOT cache the chain because each client has a different vectorstore.
The embedding model and Groq LLM client are lightweight to instantiate;
only the FAISS index load is the expensive operation.

Function:
    run_rag_query(client_id, question) → dict
"""

import logging
from typing import Any, Dict, List

from fastapi import HTTPException, status
from langchain_groq import ChatGroq
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.core.vectorstore import load_client_vectorstore

logger = logging.getLogger(__name__)


def _build_llm() -> ChatGroq:
    """Instantiate the Groq LLM client."""
    if not settings.GROQ_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GROQ_API_KEY is not set. Please add it to your .env file.",
        )
    return ChatGroq(
        model=settings.GROQ_MODEL_NAME,
        temperature=0.5,
        max_tokens=512,
        api_key=settings.GROQ_API_KEY,
    )


def run_rag_query(client_id: str, question: str) -> Dict[str, Any]:
    """
    Run a RAG query for a specific client.

    Steps:
        1. Load client's FAISS vector store
        2. Build retriever (top-K semantic search)
        3. Pull the LangChain RAG prompt from LangChain Hub
        4. Create stuff-documents chain (inject retrieved docs into prompt)
        5. Create retrieval chain (retriever + document chain)
        6. Invoke with the user's question
        7. Return answer + formatted source references

    Args:
        client_id: UUID of the tenant whose documents to search.
        question:  The user's question string.

    Returns:
        dict with keys:
            - "answer"  (str): The LLM-generated answer
            - "sources" (list): List of source chunk metadata dicts

    Raises:
        HTTPException 404: If client has no uploaded documents.
        HTTPException 500: If Groq API key is missing or call fails.
    """
    logger.info(f"[{client_id}] Running RAG query: {question[:80]}")

    # ── Step 1: Load client's FAISS index ────────────────────────────────────
    db = load_client_vectorstore(client_id)

    # ── Step 2: Build retriever ───────────────────────────────────────────────
    retriever = db.as_retriever(
        search_type="similarity",
        search_kwargs={"k": settings.RETRIEVAL_TOP_K},
    )

    # ── Step 3: Local RAG prompt definition ───────────────────────────────────
    retrieval_qa_chat_prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer the user's question using the provided context. If you don't know the answer, say that you don't know, don't try to make up an answer.\n\nContext:\n{context}"),
        ("human", "{input}"),
    ])

    # ── Step 4: Build document-stuffing chain ─────────────────────────────────
    llm = _build_llm()
    combine_docs_chain = create_stuff_documents_chain(llm, retrieval_qa_chat_prompt)

    # ── Step 5: Wrap into full retrieval chain ────────────────────────────────
    rag_chain = create_retrieval_chain(retriever, combine_docs_chain)

    # ── Step 6: Invoke ────────────────────────────────────────────────────────
    try:
        response = rag_chain.invoke({"input": question})
    except Exception as e:
        logger.error(f"[{client_id}] RAG chain error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating answer: {str(e)}",
        )

    # ── Step 7: Extract answer and sources ────────────────────────────────────
    answer = response.get("answer", "I could not generate an answer.")

    source_docs = response.get("context", [])
    sources = [
        {
            "source": doc.metadata.get("source", "Unknown"),
            "page": doc.metadata.get("page", "N/A"),
            "snippet": doc.page_content[:200],
        }
        for doc in source_docs
    ]

    logger.info(f"[{client_id}] Answer generated. Sources: {[s['source'] for s in sources]}")

    return {
        "answer": answer,
        "sources": sources,
    }
