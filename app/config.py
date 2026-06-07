"""
app/config.py
─────────────
Central configuration for CampConnect SaaS.
All settings are loaded from environment variables (or .env file).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (one level up from this file)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")


class Settings:
    # ── Project Root ─────────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent.parent

    # ── Vector Store ──────────────────────────────────────────────────────────
    # Per-client FAISS indexes are stored at:
    #   vectorstore/{client_id}/db_faiss/
    VECTORSTORE_BASE: Path = BASE_DIR / "vectorstore"

    # ── Embedding Model ───────────────────────────────────────────────────────
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── Groq LLM ─────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL_NAME: str = "llama-3.1-8b-instant"

    # ── MySQL Database ────────────────────────────────────────────────────────
    # Format: mysql+pymysql://user:password@host:port/dbname
    MYSQL_URL: str = ""

    def __init__(self):
        # 1. Check if SQLite is explicitly requested
        use_sqlite = os.getenv("USE_SQLITE", "").lower() in ("true", "1", "yes")

        # 2. Get connection URLs first
        url = os.getenv("MYSQL_URL") or os.getenv("DATABASE_URL")

        if use_sqlite:
            # Use SQLite database in the data directory
            self.MYSQL_URL = "sqlite:///data/campconnect.db"
        elif url:
            # Prioritize complete connection URL if provided
            if url.startswith("mysql://"):
                url = url.replace("mysql://", "mysql+pymysql://", 1)
            self.MYSQL_URL = url
        else:
            # 3. Fallback to individual variables if no complete URL is provided
            mysql_host = os.getenv("MYSQLHOST") or os.getenv("MYSQL_HOST")
            mysql_port = os.getenv("MYSQLPORT") or os.getenv("MYSQL_PORT") or "3306"
            mysql_user = os.getenv("MYSQLUSER") or os.getenv("MYSQL_USER")
            mysql_pass = os.getenv("MYSQLPASSWORD") or os.getenv("MYSQL_PASSWORD")
            mysql_db = os.getenv("MYSQLDATABASE") or os.getenv("MYSQL_DATABASE")

            if mysql_host and mysql_user and mysql_db:
                self.MYSQL_URL = f"mysql+pymysql://{mysql_user}:{mysql_pass or ''}@{mysql_host}:{mysql_port}/{mysql_db}"
            else:
                # 4. Default to SQLite instead of failing with MySQL connection error
                self.MYSQL_URL = "sqlite:///data/campconnect.db"

    # ── JWT Auth (used in Task 2) ─────────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-in-production-please")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # ── RAG Retrieval ─────────────────────────────────────────────────────────
    RETRIEVAL_TOP_K: int = 3
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # ── College Config ────────────────────────────────────────────────────────
    COLLEGE_CLIENT_ID: str = os.getenv("COLLEGE_CLIENT_ID", "")



# Single shared settings instance — import this everywhere
settings = Settings()
