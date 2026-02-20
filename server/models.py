from datetime import datetime

from sqlalchemy import Boolean, Integer, String, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    amount: Mapped[int] = mapped_column(Integer)
    vendor: Mapped[str] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    raw_text: Mapped[str] = mapped_column(String)
    transaction_date: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Tester(Base):
    __tablename__ = "testers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, default="")
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, default="사용자")
    monthly_budget: Mapped[int] = mapped_column(Integer, default=1_000_000)  # 월 예산 (기본 100만원)
    fixed_expenses: Mapped[int] = mapped_column(Integer, default=300_000)    # 월 고정비 (기본 30만원)
