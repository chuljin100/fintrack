import json
import os
import logging

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

PACKAGE_NAME = "com.fintrack.app"
TRACK = "internal"

SCOPES = ["https://www.googleapis.com/auth/androidpublisher"]


def _get_service():
    """Google Play Developer API 서비스 클라이언트 생성."""
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON 환경변수가 설정되지 않았습니다")

    creds_info = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(
        creds_info, scopes=SCOPES
    )
    return build("androidpublisher", "v3", credentials=credentials)


def add_tester_to_internal_track(email: str) -> dict:
    """
    Play Store 내부 테스트 트랙에 테스터 이메일을 추가.
    edit → testers 수정 → commit 순서로 진행.
    """
    service = _get_service()
    edits = service.edits()

    # 1. edit 생성
    edit = edits.insert(packageName=PACKAGE_NAME, body={}).execute()
    edit_id = edit["id"]

    try:
        # 2. 현재 테스터 목록 가져오기
        testers = edits.testers().get(
            packageName=PACKAGE_NAME, editId=edit_id, track=TRACK
        ).execute()

        current_emails = testers.get("googleEmails", [])

        # 3. 이미 등록된 이메일인지 확인
        if email in current_emails:
            return {"status": "already_exists", "email": email}

        # 4. 새 이메일 추가
        current_emails.append(email)
        edits.testers().patch(
            packageName=PACKAGE_NAME,
            editId=edit_id,
            track=TRACK,
            body={"googleEmails": current_emails},
        ).execute()

        # 5. edit 커밋
        edits.commit(packageName=PACKAGE_NAME, editId=edit_id).execute()

        logger.info(f"테스터 추가 완료: {email}")
        return {"status": "added", "email": email, "total": len(current_emails)}

    except Exception as e:
        # 실패 시 edit 삭제
        try:
            edits.delete(packageName=PACKAGE_NAME, editId=edit_id).execute()
        except Exception:
            pass
        logger.error(f"테스터 추가 실패: {email} - {e}")
        raise
