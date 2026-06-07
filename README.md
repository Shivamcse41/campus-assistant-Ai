# 🎓 CampConnect (RAG-based Campus Assistant)

CampConnect is a multi-tenant RAG (Retrieval-Augmented Generation) SaaS application designed for college campuses. It allows college staff members to upload documents (admission forms, fee structures, syllabus, rules, etc.) to build a shared FAISS vector store, enabling students to instantly query college information via an AI-powered chat interface.

---

## ✨ Features

### 🏫 GPA Assistant (Special College Customization)
Tailored integration for **Government Polytechnic Aurangabad** (GPA):
- **Shared Staff Indexing**: All registered staff members share a single college client ID (`COLLEGE_CLIENT_ID` in `.env`). PDFs uploaded by any staff member are merged into one shared FAISS index.
- **Student Chat Interface (`static/student.html`)**: A beautiful, full-screen dark-themed chat UI modeled after Claude.ai. Guest access (no login required) with recommended question chips, mobile responsiveness, and source document mapping.
- **Public Query Endpoint**: `POST /api/query/public/{client_id}` provides guest RAG query access with rate limiting (**20 queries per IP per hour**) via `slowapi` to prevent abuse.

### 🤖 Core RAG & Tech Stack
- **FastAPI Backend**: High-performance asynchronous API endpoints.
- **LangChain & Groq (Llama 3.1)**: State-of-the-art context-aware response generation.
- **FAISS Vector Database**: Fast semantic local vector search.
- **Sentence-Transformers (`all-MiniLM-L6-v2`)**: Local embeddings generation.
- **MySQL Database**: Persistent storage for tenant clients, document uploads metadata, and query logging.
- **JWT Authentication**: Secure endpoints protecting staff/admin document management operations.

---

## 🏗 Project Structure

```
├── app/
│   ├── api/
│   │   └── routes.py         # Main routes including public and staff APIs
│   ├── auth/
│   │   ├── dependencies.py   # JWT authentication validation
│   │   ├── router.py         # Login and registration routes
│   │   └── utils.py          # Password hashing and token generation
│   ├── core/
│   │   ├── embeddings.py     # SentenceTransformer embeddings caching
│   │   ├── rag_pipeline.py   # LangChain RAG query execution logic
│   │   └── vectorstore.py    # FAISS local vector store creation/management
│   ├── config.py             # Configuration loader
│   ├── database.py           # MySQL database configuration
│   ├── models.py             # SQLAlchemy ORM models
│   └── main.py               # FastAPI application entrypoint
├── static/
│   ├── css/                  # Styling assets
│   ├── js/                   # Frontend dashboard & widget scripts
│   ├── dashboard.html        # Staff admin document upload dashboard
│   ├── login.html            # Staff/Admin login UI
│   └── student.html          # Public-facing Student Chat Portal
├── run.py                    # Main development server runner
├── requirements.txt          # Python dependencies
└── .env                      # Local environment configuration
```

---

## ⚙️ Installation & Setup

### 1. Clone & Set Up Environment
Copy `.env.example` to `.env` and configure the settings:
```bash
cp .env.example .env
```
Inside `.env`, configure:
- `GROQ_API_KEY`: Your Groq API key for Llama-3.1 generation.
- `SECRET_KEY`: Long random string for JWT encryption.
- `MYSQL_URL`: Connection string to your MySQL database.
- `COLLEGE_CLIENT_ID`: A fixed UUID for the college client (e.g. `4a78c1ab-98db-4e12-b5fb-df98a9643d92`).

### 2. Install Dependencies
Create a virtual environment and install the required libraries:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🚀 Running the Application

### 1. Start the Server
Run the convenience script to start the FastAPI server:
```bash
python run.py
```
This automatically sets up all MySQL tables and seeds the default college client using the `COLLEGE_CLIENT_ID` defined in `.env`.

### 2. Access Portals
- **Student Chat Portal**: [http://localhost:8000/static/student.html](http://localhost:8000/static/student.html)
- **Staff Admin Dashboard**: [http://localhost:8000/static/login.html](http://localhost:8000/static/login.html)
- **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
