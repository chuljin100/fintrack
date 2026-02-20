import os
import logging
import urllib.request
import urllib.parse
import json

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7816442753:AAE574WLSxoW3t4_B1pYRdP7Y_2atSib5Xs")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "857266638")


def send_new_tester_alert(email: str, name: str):
    """새 테스터 등록 시 텔레그램 알림 전송."""
    text = (
        f"🆕 새 테스터 신청!\n\n"
        f"📧 이메일: {email}\n"
        f"👤 이름: {name or '(미입력)'}\n\n"
        f"👉 Play Console에 추가해주세요"
    )
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": CHAT_ID, "text": text}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        logger.info(f"텔레그램 알림 전송 완료: {email}")
    except Exception as e:
        logger.error(f"텔레그램 알림 실패: {e}")
