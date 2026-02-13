import os
import logging

from openai import AsyncOpenAI
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session
from models import Transaction

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

SYSTEM_PROMPT = (
    "당신은 한국의 금융 전문가입니다. "
    "입력된 가맹점 이름을 [식비, 교통, 쇼핑, 의료, 주거, 금융, 기타] 중 하나로 분류하여 단답형으로 대답하세요."
)

VALID_CATEGORIES = {"식비", "교통", "쇼핑", "의료", "주거", "금융", "기타"}


async def classify_transaction(vendor: str) -> str:
    """가맹점 이름을 기반으로 카테고리를 분류한다."""
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": vendor},
            ],
            max_tokens=10,
            temperature=0,
        )
        category = response.choices[0].message.content.strip()
        # 유효한 카테고리인지 검증
        if category not in VALID_CATEGORIES:
            category = "기타"
        return category
    except Exception as e:
        logger.warning(f"AI 분류 실패, 규칙 기반 fallback 사용: {e}")
        return classify_by_rules(vendor)


def classify_by_rules(vendor: str) -> str:
    """키워드 기반 규칙 분류 (AI fallback)."""
    v = vendor.lower()

    food_keywords = [
        "스타벅스", "카페", "커피", "맥도날드", "버거킹", "롯데리아", "배달의민족",
        "요기요", "쿠팡이츠", "편의점", "cu", "gs25", "세븐일레븐", "이마트24",
        "김밥", "치킨", "피자", "족발", "bbq", "bhc", "교촌", "떡볶이",
        "식당", "레스토랑", "한식", "중식", "일식", "분식", "베이커리", "빵",
        "마라탕", "샐러드", "도시락", "반찬", "고기", "삼겹살", "회",
    ]
    transport_keywords = [
        "지하철", "버스", "택시", "카카오t", "타다", "코레일", "ktx",
        "srt", "고속버스", "주유소", "gs칼텍스", "sk에너지", "s-oil",
        "주차", "톨게이트", "하이패스",
    ]
    shopping_keywords = [
        "올리브영", "다이소", "쿠팡", "네이버", "무신사", "지그재그",
        "이마트", "홈플러스", "롯데마트", "코스트코", "하이마트",
        "백화점", "아울렛", "마켓", "쇼핑",
    ]
    medical_keywords = [
        "병원", "의원", "클리닉", "약국", "치과", "안과", "피부과",
        "정형외과", "내과", "이비인후과", "세브란스", "삼성서울", "아산",
    ]
    housing_keywords = [
        "관리비", "월세", "전기", "가스", "수도", "통신", "kt", "skt",
        "lg유플러스", "인터넷", "아파트",
    ]
    finance_keywords = [
        "보험", "적금", "대출", "증권", "투자", "은행", "카드",
        "수수료", "이자",
    ]

    for kw in food_keywords:
        if kw in v:
            return "식비"
    for kw in transport_keywords:
        if kw in v:
            return "교통"
    for kw in shopping_keywords:
        if kw in v:
            return "쇼핑"
    for kw in medical_keywords:
        if kw in v:
            return "의료"
    for kw in housing_keywords:
        if kw in v:
            return "주거"
    for kw in finance_keywords:
        if kw in v:
            return "금융"

    return "기타"


async def classify_and_update(transaction_id: int, vendor: str):
    """백그라운드에서 AI 분류를 수행하고 DB를 업데이트한다."""
    category = await classify_transaction(vendor)

    async with async_session() as session:
        await session.execute(
            update(Transaction)
            .where(Transaction.id == transaction_id)
            .values(category=category)
        )
        await session.commit()

    logger.info(f"거래 #{transaction_id} 카테고리 업데이트: {vendor} → {category}")
