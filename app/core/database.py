from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    # Ensure vector extension exists
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
        
    Base.metadata.create_all(bind=engine)

    # Perform idempotent column migrations for pre-existing database volumes
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE future_activities 
            ADD COLUMN IF NOT EXISTS target_activity_id VARCHAR(36) REFERENCES current_activities(id) ON DELETE SET NULL;
        """))
        conn.execute(text("""
            ALTER TABLE research_evidence 
            ADD COLUMN IF NOT EXISTS transformation_run_id VARCHAR(36) REFERENCES future_processes(id) ON DELETE CASCADE;
        """))
        conn.commit()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
