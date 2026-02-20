import calendar
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, init_db
from models import Tester, Transaction, User
from schemas import (
    DailyBudgetResponse,
    ForecastRequest,
    ForecastResponse,
    TesterCreate,
    TesterRead,
    TransactionCreate,
    TransactionRead,
    UserCreate,
)
from services.ai_service import classify_and_update


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="FinTrack API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chuljin100.github.io"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────
# Transaction 엔드포인트
# ──────────────────────────────────────────


@app.post("/transactions", response_model=TransactionRead)
async def create_transaction(
    data: TransactionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """거래 내역 생성. 저장 후 백그라운드로 AI 카테고리 분류를 실행."""
    txn = Transaction(
        user_id=data.user_id,
        amount=data.amount,
        vendor=data.vendor,
        raw_text=data.raw_text,
        transaction_date=data.transaction_date,
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)

    # 응답을 먼저 보내고 백그라운드에서 AI 분류 실행
    background_tasks.add_task(classify_and_update, txn.id, txn.vendor)

    return txn


@app.get("/transactions", response_model=list[TransactionRead])
async def list_transactions(
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """사용자의 거래 내역 조회."""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.desc())
    )
    return result.scalars().all()


# ──────────────────────────────────────────
# 일일 예산 API
# ──────────────────────────────────────────


@app.get("/budget/daily", response_model=DailyBudgetResponse)
async def get_daily_budget(
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    오늘 쓸 수 있는 돈 계산.
    = (월 예산 - 고정비 - 이번 달 총 지출) / 남은 일수
    """
    # 사용자 정보 조회
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    now = datetime.utcnow()
    # 이번 달 1일 00:00
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # 이번 달 마지막 날
    _, last_day = calendar.monthrange(now.year, now.month)
    month_end = now.replace(day=last_day, hour=23, minute=59, second=59)

    # 이번 달 총 지출
    spent_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= month_start,
            Transaction.transaction_date <= month_end,
        )
    )
    spent_this_month = spent_result.scalar()

    # 남은 금액 = 월 예산 - 고정비 - 지출
    remaining = user.monthly_budget - user.fixed_expenses - spent_this_month

    # 남은 일수 (오늘 포함)
    days_left = last_day - now.day + 1

    daily_budget = max(remaining // days_left, 0) if days_left > 0 else 0

    return DailyBudgetResponse(
        daily_budget=daily_budget,
        remaining_this_month=max(remaining, 0),
        days_left=days_left,
        spent_this_month=spent_this_month,
    )


# ──────────────────────────────────────────
# 미래 예측 API
# ──────────────────────────────────────────


@app.post("/plan/forecast", response_model=ForecastResponse)
async def forecast(
    data: ForecastRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    목표 금액 달성 가능 여부 예측.
    과거 3개월 평균 저축액 기반 선형 예측.
    """
    # 사용자 정보 조회
    result = await db.execute(select(User).where(User.user_id == data.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    now = datetime.utcnow()

    # 최근 3개월 월별 지출 계산
    monthly_savings = []
    for i in range(1, 4):
        # i개월 전
        target_month = now.month - i
        target_year = now.year
        if target_month <= 0:
            target_month += 12
            target_year -= 1

        _, last_day = calendar.monthrange(target_year, target_month)
        m_start = datetime(target_year, target_month, 1)
        m_end = datetime(target_year, target_month, last_day, 23, 59, 59)

        spent_result = await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == data.user_id,
                Transaction.transaction_date >= m_start,
                Transaction.transaction_date <= m_end,
            )
        )
        spent = spent_result.scalar()

        # 저축액 = 월 예산 - 지출
        saving = user.monthly_budget - spent
        monthly_savings.append(saving)

    # 평균 월 저축액
    avg_saving = sum(monthly_savings) // len(monthly_savings) if monthly_savings else 0

    # 예측 총 저축액 (기간 * 월 평균 저축)
    projected_total = avg_saving * data.months

    achievable = projected_total >= data.target_amount
    deficit = max(data.target_amount - projected_total, 0)

    return ForecastResponse(
        achievable=achievable,
        monthly_saving_avg=avg_saving,
        projected_total=projected_total,
        deficit=deficit,
    )


# ──────────────────────────────────────────
# User 엔드포인트 (편의용)
# ──────────────────────────────────────────


@app.post("/users")
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """사용자 생성."""
    user = User(
        user_id=data.user_id,
        name=data.name,
        monthly_budget=data.monthly_budget,
        fixed_expenses=data.fixed_expenses,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "user_id": user.user_id}


# ──────────────────────────────────────────
# 테스터 등록 엔드포인트
# ──────────────────────────────────────────


@app.post("/testers", response_model=TesterRead)
async def register_tester(
    data: TesterCreate,
    db: AsyncSession = Depends(get_db),
):
    """테스터 이메일 등록."""
    existing = await db.execute(select(Tester).where(Tester.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 등록된 이메일입니다")
    tester = Tester(email=data.email, name=data.name)
    db.add(tester)
    await db.commit()
    await db.refresh(tester)
    return tester


@app.get("/testers", response_model=list[TesterRead])
async def list_testers(db: AsyncSession = Depends(get_db)):
    """등록된 테스터 목록 조회."""
    result = await db.execute(select(Tester).order_by(Tester.created_at.desc()))
    return result.scalars().all()


@app.get("/testers/emails")
async def export_tester_emails(db: AsyncSession = Depends(get_db)):
    """Play Console에 복사할 수 있는 이메일 목록 반환."""
    result = await db.execute(select(Tester.email).order_by(Tester.created_at))
    emails = [row[0] for row in result.all()]
    return {"count": len(emails), "emails": emails, "csv": ",".join(emails)}
