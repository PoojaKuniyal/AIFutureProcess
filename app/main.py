from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db, SessionLocal
from app.db.seed_data import seed_initial_processes
from app.api.v1.processes import router as processes_router
from app.api.v1.transform import router as transform_router

app = FastAPI(
    title="AI Future Process Designer API",
    description="Enterprise AI Retail Process Analysis & Future-State Transformation Monolith",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()
    db = SessionLocal()
    try:
        seed_initial_processes(db)
    finally:
        db.close()

@app.get("/api/v1/health")
def health_check():
    tracing_enabled = settings.LANGCHAIN_TRACING_V2.lower() in ["true", "1"] and bool(settings.LANGCHAIN_API_KEY)
    return {
        "status": "healthy",
        "llm_provider": settings.LLM_PROVIDER,
        "search_provider": settings.SEARCH_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "langsmith_tracing_enabled": tracing_enabled,
        "langsmith_project": settings.LANGCHAIN_PROJECT if tracing_enabled else None
    }

app.include_router(processes_router, prefix="/api/v1")
app.include_router(transform_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)
