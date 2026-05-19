from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Import DB (must come before models)
from app.database.db import Base, engine, wait_for_db

# Import all models so they register with SQLAlchemy metadata
from app.models import developer_model, repo_model, scan_job_model, issue_model  # noqa

# Import Routers
from app.api.routes_scan import router as scan_router
from app.api.routes_repos import router as repos_router
from app.api.routes_scans import router as scans_router
from app.api.routes_issues import router as issues_router
from app.api.routes_status import router as status_router
from app.api.routes_chat import router as chat_router

# Create FastAPI app
app = FastAPI(
    title="AI Code Reviewer API",
    version="1.0.0",
    description="AI-powered code review using Groq LLMs"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB tables on startup
Base.metadata.create_all(bind=engine)

# Register Routes
app.include_router(scan_router, prefix="/api", tags=["Scan"])
app.include_router(repos_router, prefix="/api", tags=["Repositories"])
app.include_router(scans_router, prefix="/api", tags=["Scans"])
app.include_router(issues_router, prefix="/api", tags=["Issues"])
app.include_router(status_router, prefix="/api", tags=["Scan Status"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])


@app.get("/")
def root():
    return {"message": "AI Code Reviewer Backend Running 🚀"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc)}
    )