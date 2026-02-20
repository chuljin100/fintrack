import asyncio
import os
import logging
import urllib.request
import json

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7816442753:AAE574WLSxoW3t4_B1pYRdP7Y_2atSib5Xs")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "857266638")
CHECK_INTERVAL = 300  # 5분


def _send_telegram(text: str):
    """텔레그램 메시지 전송."""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": CHAT_ID, "text": text}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        logger.error(f"텔레그램 알림 실패: {e}")


async def tester_check_loop(async_session_factory):
    """5분마다 신규 테스터를 확인하고 알림 전송."""
    from models import Tester

    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        try:
            async with async_session_factory() as db:
                result = await db.execute(
                    select(Tester).where(Tester.notified == False)
                )
                new_testers = result.scalars().all()

                if not new_testers:
                    continue

                lines = []
                for t in new_testers:
                    lines.append(f"  📧 {t.email} ({t.name or '미입력'})")

                text = (
                    f"🆕 새 테스터 {len(new_testers)}명 신청!\n\n"
                    + "\n".join(lines)
                    + "\n\n👉 Play Console에 추가해주세요"
                )
                _send_telegram(text)

                # 알림 완료 표시
                ids = [t.id for t in new_testers]
                await db.execute(
                    update(Tester).where(Tester.id.in_(ids)).values(notified=True)
                )
                await db.commit()
                logger.info(f"신규 테스터 {len(new_testers)}명 알림 전송 완료")

        except Exception as e:
            logger.error(f"테스터 체크 루프 오류: {e}")
