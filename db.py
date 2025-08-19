from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import os

engine = None
SessionLocal = None

def setup_db(base_metadata):
    global engine, SessionLocal
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bot.db")
    engine = create_engine(DATABASE_URL, echo=True)
    base_metadata.create_all(bind=engine) # Create tables here
    SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_session():
    return SessionLocal()