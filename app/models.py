"""
app/models.py
─────────────
SQLAlchemy ORM models for the CampConnect multi-tenant platform.

Tables:
  - clients     → one row per business/tenant
  - documents   → tracks each uploaded PDF per client
  - query_logs  → records every chatbot query + answer per client
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Text, DateTime, ForeignKey, func
)
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    """Generate a new UUID4 string for primary keys."""
    return str(uuid.uuid4())


# ── Client (Tenant) ───────────────────────────────────────────────────────────
class Client(Base):
    __tablename__ = "clients"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    business_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    documents = relationship("Document", back_populates="client", cascade="all, delete-orphan")
    query_logs = relationship("QueryLog", back_populates="client", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Client id={self.id} email={self.email} business={self.business_name}>"


# ── Document (Uploaded PDF) ───────────────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(512), nullable=False)
    num_chunks = Column(Integer, default=0)          # How many text chunks were created
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship back to client
    client = relationship("Client", back_populates="documents")

    def __repr__(self):
        return f"<Document id={self.id} client={self.client_id} file={self.filename}>"


# ── Query Log ─────────────────────────────────────────────────────────────────
class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship back to client
    client = relationship("Client", back_populates="query_logs")

    def __repr__(self):
        return f"<QueryLog id={self.id} client={self.client_id} q={self.question[:40]}>"
