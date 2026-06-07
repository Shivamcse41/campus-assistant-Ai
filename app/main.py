"""
app/main.py
───────────
CampConnect SaaS — FastAPI application entry point.

This module:
    - Creates the FastAPI app instance
    - Configures CORS (for the embeddable widget — Task 4)
    - Auto-creates all MySQL tables on startup
    - Registers all API routers
    - Provides a health check endpoint
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base, SessionLocal
from app.api.routes import router as api_router, limiter
from app.auth.router import router as auth_router
from slowapi.errors import RateLimitExceeded
from slowapi.extension import _rate_limit_exceeded_handler

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on application startup and shutdown.
    - Creates all database tables if they don't exist yet (safe to run repeatedly)
    - Seeds the fixed COLLEGE_CLIENT_ID if it is set in settings but does not exist in DB
    - Pre-warms the embedding model so the first request isn't slow
    """
    logger.info("═" * 60)
    logger.info("  CampConnect SaaS — Starting up")
    logger.info("═" * 60)

    # Auto-create MySQL tables (idempotent)
    logger.info("Creating database tables if not exist...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready.")

    # Seed COLLEGE_CLIENT_ID client if configured
    from app.config import settings
    from app.models import Client
    if settings.COLLEGE_CLIENT_ID:
        db = SessionLocal()
        try:
            college_client = db.query(Client).filter(Client.id == settings.COLLEGE_CLIENT_ID).first()
            if not college_client:
                logger.info(f"Seeding college client with ID: {settings.COLLEGE_CLIENT_ID}")
                college_client = Client(
                    id=settings.COLLEGE_CLIENT_ID,
                    business_name="Government Polytechnic Aurangabad",
                    email="admin@gpa.edu",
                    hashed_password="gpa-college-fixed-account-disabled",
                )
                db.add(college_client)
                db.commit()
                logger.info("College client seeded successfully.")
            else:
                logger.info(f"College client with ID {settings.COLLEGE_CLIENT_ID} already exists.")
        except Exception as e:
            logger.error(f"Error seeding college client: {e}")
            db.rollback()
        finally:
            db.close()

    # Pre-warm embedding model (loads ~90MB model into memory now,
    # so the first /api/upload request doesn't time out)
    logger.info("Pre-loading embedding model...")
    from app.core.embeddings import get_embedding_model
    get_embedding_model()
    logger.info("Embedding model ready.")

    logger.info("═" * 60)
    logger.info("  CampConnect SaaS is ready to serve requests")
    logger.info("  API Docs: http://localhost:8000/docs")
    logger.info("═" * 60)

    yield

    # Shutdown
    logger.info("CampConnect SaaS — Shutting down.")


# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="CampConnect SaaS",
    description="""
## CampConnect — Multi-Tenant RAG Chatbot Platform

Upload your business documents and get an AI-powered Q&A chatbot for your customers.

### Features
- 📄 **PDF Upload** — Upload any PDF and it's instantly searchable
- 🤖 **AI Answers** — Powered by Groq Llama 3.1 + LangChain RAG
- 🔒 **Multi-Tenant** — Each business gets isolated document storage
- 🌐 **Embeddable Widget** — Paste one script tag to add the chatbot to any website

### Authentication
All `/api/*` endpoints will require a JWT Bearer token (Task 2).
For Task 1 testing, use the `/api/clients/register-demo` endpoint.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)



# ── CORS Middleware ────────────────────────────────────────────────────────────
# Allows the embeddable JS widget (Task 4) to call the API from any origin.
# In production, restrict this to your own domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Restrict in production: ["https://yourdomain.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)   # POST /auth/register, POST /auth/login, GET /auth/me
app.include_router(api_router)    # POST /api/upload, /api/query, GET /api/clients, DELETE /api/client


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"], summary="Health check")
def health_check():
    """Returns 200 OK if the server is running."""
    return {
        "status": "healthy",
        "service": "CampConnect SaaS",
        "version": "1.0.0",
    }


@app.get("/", tags=["Root"], summary="API root")
def root():
    """Redirect users to the student chat page."""
    return RedirectResponse(url="/static/student.html")



# Serve static files (HTML, CSS, JS) from the static/ directory
app.mount("/static", StaticFiles(directory="static"), name="static")

