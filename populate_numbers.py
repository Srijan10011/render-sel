
import os
import random
from dotenv import load_dotenv

from db import SessionLocal, engine, init_db
from models import Number, StatusEnum

load_dotenv()

def populate_numbers(num_numbers: int = 5):
    init_db()  # Ensure tables are created
    with SessionLocal() as session:
        for i in range(num_numbers):
            phone = f"+1555{random.randint(1000000, 9999999)}"
            gs_token = f"gs_token_{random.randint(10000, 99999)}"
            
            # Check if number or gs_token already exists to avoid duplicates
            existing_number = session.query(Number).filter_by(phone=phone).first()
            existing_gs_token = session.query(Number).filter_by(gs_token=gs_token).first()

            if not existing_number and not existing_gs_token:
                number = Number(phone=phone, gs_token=gs_token, status=StatusEnum.free)
                session.add(number)
                print(f"Added number: {phone} with gs_token: {gs_token}")
            else:
                print(f"Skipped adding number (duplicate found): {phone} or {gs_token}")

        session.commit()
    print(f"Finished populating {num_numbers} numbers.")

if __name__ == "__main__":
    populate_numbers(10) # Add 10 dummy numbers
