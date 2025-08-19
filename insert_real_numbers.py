import os
from dotenv import load_dotenv

import db
from models import Base, Number, StatusEnum

load_dotenv()

def insert_real_numbers():
    # Initialize database connection and create tables if they don't exist
    db.setup_db(Base.metadata)

    # IMPORTANT: Replace with your actual phone numbers and gs_tokens
    # Each tuple should be (phone_number_string, gs_token_string)
    numbers_to_insert = [
       
        ("+12894724620", "ukbqlbo77we")
    ]

    with db.SessionLocal() as session:
        for phone, gs_token in numbers_to_insert:
            existing_number = session.query(Number).filter_by(phone=phone).first()
            if existing_number:
                print(f"Number {phone} already exists. Skipping.")
            else:
                number = Number(phone=phone, gs_token=gs_token, status=StatusEnum.free)
                session.add(number)
                print(f"Added number: {phone} with gs_token: {gs_token}")
        session.commit()
    print("Finished inserting real numbers.")

if __name__ == "__main__":
    insert_real_numbers()
