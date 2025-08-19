import datetime
import enum

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    BigInteger,
    Enum,
    JSON,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class StatusEnum(enum.Enum):
    free = "free"
    assigned = "assigned"
    retired = "retired"


class ReasonEnum(enum.Enum):
    purchase = "purchase"
    admin_grant = "admin_grant"
    get_account = "get_account"
    refund_remove = "refund_remove"
    admin_set_adjust = "admin_set_adjust"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String)
    is_admin = Column(Boolean, default=False, nullable=False)
    credits = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    assignments = relationship("Assignment", back_populates="user")
    credit_transactions = relationship("CreditTransaction", back_populates="user")


class Number(Base):
    __tablename__ = "numbers"

    id = Column(Integer, primary_key=True)
    phone = Column(String, unique=True, nullable=False)
    gs_token = Column(String, unique=True, nullable=False)
    status = Column(Enum(StatusEnum), default=StatusEnum.free, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    assignments = relationship("Assignment", back_populates="number")


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    number_id = Column(Integer, ForeignKey("numbers.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    released_at = Column(DateTime)
    code_fetched_at = Column(DateTime)
    last_code = Column(String)
    active = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="assignments")
    number = relationship("Number", back_populates="assignments")
    credit_transactions_rel = relationship(
        "CreditTransaction", back_populates="assignment"
    )


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    delta = Column(Integer, nullable=False)
    reason = Column(Enum(ReasonEnum), nullable=False)
    ref_assignment_id = Column(Integer, ForeignKey("assignments.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    meta = Column(JSON)

    user = relationship("User", back_populates="credit_transactions")
    assignment = relationship("Assignment", back_populates="credit_transactions_rel")


class ArchivedAssignment(Base):
    __tablename__ = "archived_assignments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    number_id = Column(Integer, nullable=False)
    assigned_at = Column(DateTime, nullable=False)
    released_at = Column(DateTime, nullable=False)
    code_fetched_at = Column(DateTime)
    last_code = Column(String)