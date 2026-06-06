"""
app/core/vectorstore.py
────────────────────────
Per-client FAISS vector store management.

Each client's FAISS index lives at:
    vectorstore/{client_id}/db_faiss/

Functions:
    get_client_faiss_path(client_id)  → Path
    build_and_save_vectorstore(client_id, file_bytes, filename) → int (chunk count)
    load_client_vectorstore(client_id) → FAISS
    delete_client_vectorstore(client_id) → None
    client_vectorstore_exists(client_id) → bool
"""

import io
import shutil
import logging
import tempfile
from pathlib import Path
from typing import List

from fastapi import HTTPException, status
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from app.config import settings
from app.core.embeddings import get_embedding_model

logger = logging.getLogger(__name__)


# ── Path Helpers ──────────────────────────────────────────────────────────────

def get_client_faiss_path(client_id: str) -> Path:
    """
    Returns the absolute path to a client's FAISS index directory.
    Path: vectorstore/{client_id}/db_faiss
    """
    return settings.VECTORSTORE_BASE / client_id / "db_faiss"


def client_vectorstore_exists(client_id: str) -> bool:
    """Returns True if the client has an existing FAISS index on disk."""
    faiss_path = get_client_faiss_path(client_id)
    return (faiss_path / "index.faiss").exists()


# ── Build & Save ──────────────────────────────────────────────────────────────

def build_and_save_vectorstore(
    client_id: str,
    file_bytes: bytes,
    filename: str,
) -> int:
    """
    Process a PDF file and create/update the client's FAISS vector store.

    Steps:
        1. Write bytes to a temp file (PyPDFLoader needs a file path)
        2. Load pages with PyPDFLoader
        3. Chunk text with RecursiveCharacterTextSplitter
        4. Embed chunks with the shared HuggingFace model
        5. If client already has a FAISS index → merge new docs in
           Otherwise → create fresh FAISS index
        6. Save to disk at vectorstore/{client_id}/db_faiss/

    Args:
        client_id:  UUID string identifying the tenant
        file_bytes: Raw bytes of the uploaded PDF file
        filename:   Original filename (stored in document metadata)

    Returns:
        int: Number of text chunks embedded and stored.

    Raises:
        HTTPException 422: If the PDF cannot be parsed or is empty.
    """
    faiss_path = get_client_faiss_path(client_id)
    embedding_model = get_embedding_model()

    # ── Step 1: Write PDF bytes to a temporary file ───────────────────────────
    # PyPDFLoader requires a real filesystem path, not an in-memory buffer.
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        # ── Step 2: Load PDF pages ────────────────────────────────────────────
        loader = PyPDFLoader(tmp_path)
        pages = loader.load()

        if not pages:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not extract any text from '{filename}'. Is it a scanned/image PDF?",
            )

        # Inject original filename into each page's metadata for source tracking
        for page in pages:
            page.metadata["source"] = filename

        # ── Step 3: Chunk text ────────────────────────────────────────────────
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        chunks = splitter.split_documents(pages)

        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"PDF '{filename}' had content but produced no text chunks.",
            )

        logger.info(f"[{client_id}] Created {len(chunks)} chunks from '{filename}'")

        # ── Steps 4 & 5: Embed and store ─────────────────────────────────────
        if client_vectorstore_exists(client_id):
            # Merge into existing index (supports multiple document uploads)
            logger.info(f"[{client_id}] Merging into existing FAISS index")
            existing_db = FAISS.load_local(
                str(faiss_path),
                embedding_model,
                allow_dangerous_deserialization=True,
            )
            new_db = FAISS.from_documents(chunks, embedding_model)
            existing_db.merge_from(new_db)
            existing_db.save_local(str(faiss_path))
        else:
            # Create fresh index for this client
            logger.info(f"[{client_id}] Creating new FAISS index")
            faiss_path.mkdir(parents=True, exist_ok=True)
            db = FAISS.from_documents(chunks, embedding_model)
            db.save_local(str(faiss_path))

        logger.info(f"[{client_id}] FAISS index saved at: {faiss_path}")
        return len(chunks)

    finally:
        # ── Cleanup: always remove the temp file ──────────────────────────────
        Path(tmp_path).unlink(missing_ok=True)


# ── Load ──────────────────────────────────────────────────────────────────────

def load_client_vectorstore(client_id: str) -> FAISS:
    """
    Load an existing FAISS index for a client.

    Args:
        client_id: UUID string of the tenant.

    Returns:
        FAISS: The loaded vector store.

    Raises:
        HTTPException 404: If no vectorstore exists for this client.
    """
    faiss_path = get_client_faiss_path(client_id)

    if not client_vectorstore_exists(client_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No documents have been uploaded for client '{client_id}' yet. "
                   f"Please upload a PDF first via POST /api/upload/{client_id}",
        )

    logger.info(f"[{client_id}] Loading FAISS index from: {faiss_path}")
    return FAISS.load_local(
        str(faiss_path),
        get_embedding_model(),
        allow_dangerous_deserialization=True,
    )


# ── Delete ────────────────────────────────────────────────────────────────────

def delete_client_vectorstore(client_id: str) -> None:
    """
    Remove the entire vectorstore directory for a client.

    Args:
        client_id: UUID string of the tenant.
    """
    client_dir = settings.VECTORSTORE_BASE / client_id

    if client_dir.exists():
        shutil.rmtree(client_dir)
        logger.info(f"[{client_id}] Vectorstore deleted: {client_dir}")
    else:
        logger.warning(f"[{client_id}] Vectorstore not found on disk — skipping delete.")


def delete_document_from_vectorstore(client_id: str, filename: str) -> bool:
    """
    Remove all chunks originating from `filename` from the client's FAISS vector store.
    If no chunks remain after deletion, delete the entire vector store index files.
    """
    faiss_path = get_client_faiss_path(client_id)
    if not client_vectorstore_exists(client_id):
        return False

    embedding_model = get_embedding_model()
    db = FAISS.load_local(
        str(faiss_path),
        embedding_model,
        allow_dangerous_deserialization=True,
    )

    # In FAISS, document chunks are stored in db.docstore._dict
    # Find the keys (ids) of the documents that match the filename
    ids_to_delete = []
    for doc_id, doc in db.docstore._dict.items():
        if doc.metadata.get("source") == filename:
            ids_to_delete.append(doc_id)

    if not ids_to_delete:
        return False

    # Delete chunks
    db.delete(ids_to_delete)

    # If the docstore is empty now, delete the vectorstore files from disk
    if not db.docstore._dict:
        delete_client_vectorstore(client_id)
    else:
        # Save the updated FAISS database
        db.save_local(str(faiss_path))

    logger.info(f"[{client_id}] Deleted {len(ids_to_delete)} chunks for file '{filename}' from FAISS")
    return True

