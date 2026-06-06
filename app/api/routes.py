"""
app/api/routes.py
─────────────────
All /api/* endpoints for CampConnect multi-tenant SaaS.

Endpoints (Task 2 — all routes protected by JWT Bearer auth):
    POST   /api/upload/{client_id}   — Upload PDF, embed, save FAISS
    POST   /api/query/{client_id}    — Ask a question, get RAG answer
    GET    /api/clients              — List all clients with stats
    DELETE /api/client/{client_id}   — Delete client + their vectorstore

Authentication:
    All endpoints require: Authorization: Bearer <token>
    Get a token via POST /auth/login
"""

import logging
from typing import Any, Dict, List

from fastapi import (
    APIRouter, Depends, File, HTTPException, Path, UploadFile, status
)
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Client, Document, QueryLog
from app.core.vectorstore import (
    build_and_save_vectorstore,
    delete_client_vectorstore,
    client_vectorstore_exists,
    delete_document_from_vectorstore,
)
from app.core.rag_pipeline import run_rag_query
from app.auth.dependencies import get_current_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["API"])


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, description="The question to ask the chatbot")


class QueryResponse(BaseModel):
    client_id: str
    question: str
    answer: str
    sources: List[Dict[str, Any]]


class ClientStats(BaseModel):
    client_id: str
    business_name: str
    email: str
    documents_uploaded: int
    total_queries: int
    vectorstore_ready: bool
    created_at: str


class UploadResponse(BaseModel):
    client_id: str
    filename: str
    chunks_created: int
    message: str


class DeleteResponse(BaseModel):
    client_id: str
    message: str


# ── POST /api/upload/{client_id} ──────────────────────────────────────────────

@router.post(
    "/upload/{client_id}",
    response_model=UploadResponse,
    summary="Upload a PDF and embed it into the client's FAISS vector store",
    status_code=status.HTTP_200_OK,
)
async def upload_document(
    client_id: str = Path(..., description="UUID of the client/tenant"),
    file: UploadFile = File(..., description="PDF file to upload and embed"),
    db: Session = Depends(get_db),
    current_client: Client = Depends(get_current_client),
) -> UploadResponse:
    """
    Accept a PDF file, chunk it, embed it, and save to the client's FAISS index.

    - Requires a valid JWT Bearer token (from POST /auth/login).
    - Clients can only upload to their OWN client_id.
    - If the client already has documents, the new PDF is MERGED into the existing index.
    - Records the upload in the `documents` table for tracking.

    Returns the number of text chunks created from the PDF.
    """
    # ── Enforce ownership: client can only upload to their own store ──────────
    if current_client.id != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only upload documents to your own client account.",
        )

    client = current_client

    # ── Validate file type ────────────────────────────────────────────────────
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported. Please upload a .pdf file.",
        )

    filename = file.filename
    logger.info(f"[{client_id}] Upload request received: {filename}")

    # ── Read file bytes ───────────────────────────────────────────────────────
    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # ── Process PDF → chunks → FAISS ─────────────────────────────────────────
    # This is the heavy operation — may take 5–30s depending on PDF size
    chunks_created = build_and_save_vectorstore(
        client_id=client_id,
        file_bytes=file_bytes,
        filename=filename,
    )

    # ── Record in database ────────────────────────────────────────────────────
    doc_record = Document(
        client_id=client_id,
        filename=filename,
        num_chunks=chunks_created,
    )
    db.add(doc_record)
    db.commit()

    logger.info(f"[{client_id}] Upload complete: {filename} → {chunks_created} chunks")

    return UploadResponse(
        client_id=client_id,
        filename=filename,
        chunks_created=chunks_created,
        message=f"Successfully embedded '{filename}' into the knowledge base. "
                f"Created {chunks_created} searchable chunks.",
    )


# ── POST /api/query/{client_id} ───────────────────────────────────────────────

@router.post(
    "/query/{client_id}",
    response_model=QueryResponse,
    summary="Ask a question and get an AI-powered answer from the client's documents",
    status_code=status.HTTP_200_OK,
)
def query_documents(
    client_id: str = Path(..., description="UUID of the client/tenant"),
    body: QueryRequest = ...,
    db: Session = Depends(get_db),
    current_client: Client = Depends(get_current_client),
) -> QueryResponse:
    """
    Run a RAG query against the client's uploaded documents.

    - Requires a valid JWT Bearer token (from POST /auth/login).
    - Clients can only query their OWN documents.
    - Performs semantic search in the client's FAISS vector store.
    - Sends retrieved context + question to Groq Llama 3.1.
    - Returns the answer along with source chunk references.
    - Logs the query + answer in the `query_logs` table.
    """
    # ── Enforce ownership ─────────────────────────────────────────────────────
    if current_client.id != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only query your own client documents.",
        )

    client = current_client

    logger.info(f"[{client_id}] Query: {body.question[:80]}")

    # ── Run RAG pipeline ──────────────────────────────────────────────────────
    result = run_rag_query(client_id=client_id, question=body.question)

    # ── Log query to database ─────────────────────────────────────────────────
    log = QueryLog(
        client_id=client_id,
        question=body.question,
        answer=result["answer"],
    )
    db.add(log)
    db.commit()

    return QueryResponse(
        client_id=client_id,
        question=body.question,
        answer=result["answer"],
        sources=result["sources"],
    )


# ── POST /api/query/public/{client_id} ────────────────────────────────────────

class PublicQueryResponse(BaseModel):
    client_id: str
    question: str
    answer: str
    sources: List[Dict[str, Any]]


@router.post(
    "/query/public/{client_id}",
    response_model=PublicQueryResponse,
    summary="Ask a question without JWT authentication (used by embeddable widget)",
    status_code=status.HTTP_200_OK,
)
def query_documents_public(
    client_id: str = Path(..., description="UUID of the client/tenant"),
    body: QueryRequest = ...,
    db: Session = Depends(get_db),
) -> PublicQueryResponse:
    """
    Run a RAG query against the client's uploaded documents without authentication.

    - Used by the public-facing embeddable widget.
    - Verifies that the client exists in the database.
    - Performs semantic search in the client's FAISS vector store.
    - Returns the answer along with source chunk references.
    - Logs the query to the query_logs database.
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with ID '{client_id}' does not exist.",
        )

    logger.info(f"[Public Query - {client_id}] Query: {body.question[:80]}")

    try:
        result = run_rag_query(client_id=client_id, question=body.question)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[Public Query - {client_id}] RAG query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run query. Have you uploaded documents?",
        )

    # Log query to database
    log = QueryLog(
        client_id=client_id,
        question=body.question,
        answer=result["answer"],
    )
    db.add(log)
    db.commit()

    return PublicQueryResponse(
        client_id=client_id,
        question=body.question,
        answer=result["answer"],
        sources=result["sources"],
    )



# ── GET /api/clients ──────────────────────────────────────────────────────────

@router.get(
    "/clients",
    response_model=List[ClientStats],
    summary="List all registered clients with their stats",
    status_code=status.HTTP_200_OK,
)
def list_clients(
    db: Session = Depends(get_db),
    current_client: Client = Depends(get_current_client),
) -> List[ClientStats]:
    """
    Returns a list of all clients with:
    - Number of PDFs uploaded
    - Total number of queries made
    - Whether their FAISS index is ready on disk
    """
    clients = db.query(Client).all()

    result = []
    for client in clients:
        doc_count = db.query(func.count(Document.id)).filter(
            Document.client_id == client.id
        ).scalar() or 0

        query_count = db.query(func.count(QueryLog.id)).filter(
            QueryLog.client_id == client.id
        ).scalar() or 0

        result.append(ClientStats(
            client_id=client.id,
            business_name=client.business_name,
            email=client.email,
            documents_uploaded=doc_count,
            total_queries=query_count,
            vectorstore_ready=client_vectorstore_exists(client.id),
            created_at=client.created_at.isoformat(),
        ))

    return result


# ── DELETE /api/client/{client_id} ────────────────────────────────────────────

@router.delete(
    "/client/{client_id}",
    response_model=DeleteResponse,
    summary="Delete a client and all their data",
    status_code=status.HTTP_200_OK,
)
def delete_client(
    client_id: str = Path(..., description="UUID of the client/tenant to delete"),
    db: Session = Depends(get_db),
    current_client: Client = Depends(get_current_client),
) -> DeleteResponse:
    """
    Permanently delete a client and all associated data:
    - Requires a valid JWT Bearer token.
    - Clients can only delete their OWN account.
    - Client record from MySQL (CASCADE deletes documents + query_logs).
    - Their entire vectorstore directory from disk.
    """
    # ── Enforce ownership ─────────────────────────────────────────────────────
    if current_client.id != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own client account.",
        )

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client '{client_id}' not found.",
        )

    business_name = client.business_name

    # ── Delete from MySQL (cascades to documents + query_logs) ───────────────
    db.delete(client)
    db.commit()

    # ── Delete FAISS index from disk ──────────────────────────────────────────
    delete_client_vectorstore(client_id)

    logger.info(f"Client deleted: {client_id} ({business_name})")

    return DeleteResponse(
        client_id=client_id,
        message=f"Client '{business_name}' and all their data have been permanently deleted.",
    )


# ── GET /api/documents/{client_id} ────────────────────────────────────────────

@router.get(
    "/documents/{client_id}",
    response_model=List[Dict[str, Any]],
    summary="List all uploaded documents for a client",
    status_code=status.HTTP_200_OK,
)
def list_documents(
    client_id: str = Path(..., description="UUID of the client/tenant"),
    db: Session = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """
    List all uploaded documents for the authenticated client.
    - Requires a valid JWT token.
    - Client can only view their own documents.
    """
    if current_client.id != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own documents.",
        )

    docs = db.query(Document).filter(Document.client_id == client_id).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "num_chunks": doc.num_chunks,
            "uploaded_at": doc.uploaded_at.isoformat(),
        }
        for doc in docs
    ]


# ── DELETE /api/document/{client_id}/{document_id} ─────────────────────────────

@router.delete(
    "/document/{client_id}/{document_id}",
    summary="Delete a single document and remove its chunks from FAISS",
    status_code=status.HTTP_200_OK,
)
def delete_document(
    client_id: str = Path(..., description="UUID of the client/tenant"),
    document_id: int = Path(..., description="ID of the document to delete"),
    db: Session = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """
    Delete a single document.
    - Requires a valid JWT token.
    - Client can only delete their own documents.
    - Removes the document record from MySQL.
    - Removes the corresponding embedded chunks from the FAISS vector store.
    """
    if current_client.id != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own documents.",
        )

    doc = db.query(Document).filter(
        Document.client_id == client_id,
        Document.id == document_id
    ).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    filename = doc.filename

    # Delete from database
    db.delete(doc)
    db.commit()

    # Delete from FAISS
    deleted_from_faiss = delete_document_from_vectorstore(client_id, filename)

    return {
        "client_id": client_id,
        "document_id": document_id,
        "filename": filename,
        "deleted_from_faiss": deleted_from_faiss,
        "message": f"Successfully deleted document '{filename}'."
    }

