from datetime import datetime
from pydantic import BaseModel


# --- Transaction ---

class TransactionCreate(BaseModel):
    user_id: str
    amount: int
    vendor: str
    raw_text: str
    transaction_date: datetime


class TransactionRead(BaseModel):
    id: int
    user_id: str
    amount: int
    vendor: str
    category: str | None
    raw_text: str
    transaction_date: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Budget ---

class DailyBudgetResponse(BaseModel):
    daily_budget: int
    remaining_this_month: int
    days_left: int
    spent_this_month: int


# --- Forecast ---

class ForecastRequest(BaseModel):
    user_id: str
    target_amount: int
    months: int


class ForecastResponse(BaseModel):
    achievable: bool
    monthly_saving_avg: int
    projected_total: int
    deficit: int


# --- User ---

class UserCreate(BaseModel):
    user_id: str
    name: str = "사용자"
    monthly_budget: int = 1_000_000
    fixed_expenses: int = 300_000


# --- Tester ---

class TesterCreate(BaseModel):
    email: str
    name: str = ""


class TesterRead(BaseModel):
    id: int
    email: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
