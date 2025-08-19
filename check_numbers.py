
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from models import Number, Base

# Load environment variables from .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bot.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_numbers():
    """
    Checks the numbers in the database.
    """
    db = SessionLocal()
    try:
        numbers = db.query(Number).all()
        if numbers:
            print("Numbers in the database:")
            for number in numbers:
                print(f"  - Phone: {number.phone}, Status: {number.status.name}, GS Token: {number.gs_token}")
        else:
            print("No numbers found in the database.")
    finally:
        db.close()

if __name__ == "__main__":
    check_numbers()
