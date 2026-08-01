import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
# 1. ADD THIS IMPORT:
from dotenv import load_dotenv

# 2. RUN THIS TO LOAD YOUR .ENV FILE VARIABLES:
load_dotenv()

# 3. FIX THE SPELLING PATH (Optional but safer: Hardcode it to test instantly)
database_url = os.getenv("DATABASE_URL", "postgresql://postgres:YOUR_PASSWORD@localhost:5432/ivhuredu_db")

engine = create_engine(database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
