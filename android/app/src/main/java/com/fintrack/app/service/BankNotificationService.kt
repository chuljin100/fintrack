package com.fintrack.app.service

import android.app.Notification
import android.os.Bundle
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import com.fintrack.app.data.TransactionRepository
import com.fintrack.app.di.ServiceEntryPoint
import com.fintrack.app.util.NotificationParser
import dagger.hilt.android.EntryPointAccessors
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

class BankNotificationService : NotificationListenerService() {

    companion object {
        private const val TAG = "BankNotificationService"

        private val TARGET_PACKAGES = setOf(
            "com.kakaobank.channel",        // 카카오뱅크
            "com.shinhan.sbanking",         // 신한은행
            "viva.republica.toss",          // 토스
            "com.kakao.talk",              // 카카오톡
            "com.samsung.android.messaging" // 삼성 메시지
        )
    }

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private lateinit var repository: TransactionRepository

    override fun onCreate() {
        super.onCreate()
        val entryPoint = EntryPointAccessors.fromApplication(
            applicationContext, ServiceEntryPoint::class.java
        )
        repository = entryPoint.transactionRepository()

        // 서비스 시작 시 미전송 거래 동기화
        serviceScope.launch {
            try {
                repository.syncPending()
            } catch (e: Exception) {
                Log.w(TAG, "미전송 동기화 실패: ${e.message}")
            }
        }
        Log.i(TAG, "BankNotificationService 시작됨")
    }

    override fun onDestroy() {
        serviceScope.cancel()
        super.onDestroy()
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        sbn ?: return

        val packageName = sbn.packageName
        if (packageName !in TARGET_PACKAGES) return

        Log.d(TAG, "=== 금융 알림 감지 ===")
        Log.d(TAG, "패키지: $packageName")

        val notification = sbn.notification
        val extras = notification.extras

        val title = extras.getString(Notification.EXTRA_TITLE) ?: ""
        val rawText = extractText(packageName, notification, extras)

        Log.d(TAG, "제목: $title")
        Log.d(TAG, "내용: $rawText")

        if (rawText.isBlank()) {
            Log.w(TAG, "텍스트 추출 실패 — 건너뜀")
            return
        }

        val bankName = when (packageName) {
            "com.kakaobank.channel" -> "카카오뱅크"
            "com.shinhan.sbanking" -> "신한은행"
            "viva.republica.toss" -> "토스"
            "com.kakao.talk" -> "카카오톡"
            "com.samsung.android.messaging" -> "삼성메시지"
            else -> "기타"
        }

        val combinedText = "$title $rawText"
        val transaction = NotificationParser.parse(combinedText, bankName)
        if (transaction != null) {
            Log.i(TAG, "파싱 결과: $transaction")

            // Room 저장 + 서버 전송 (코루틴으로 비동기 처리)
            serviceScope.launch {
                try {
                    repository.saveAndSync(transaction, combinedText)
                } catch (e: Exception) {
                    Log.e(TAG, "저장/전송 실패: ${e.message}")
                }
            }
        } else {
            Log.w(TAG, "파싱 실패: $combinedText")
        }
    }

    /**
     * 알림 텍스트 추출.
     * 카카오톡의 경우 MessagingStyle을 우선 확인하여 최신 메시지를 가져온다.
     * 단순 EXTRA_TEXT만 사용하면 "N개의 메시지"로만 표시될 수 있기 때문.
     */
    private fun extractText(
        packageName: String,
        notification: Notification,
        extras: Bundle
    ): String {
        // 카카오톡: MessagingStyle에서 최신 메시지 추출 시도
        if (packageName == "com.kakao.talk") {
            val messagingText = extractFromMessagingStyle(extras)
            if (!messagingText.isNullOrBlank()) {
                return messagingText
            }
        }

        // 일반 텍스트 추출 (EXTRA_BIG_TEXT -> EXTRA_TEXT 순)
        val bigText = extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString()
        if (!bigText.isNullOrBlank()) return bigText

        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString()
        if (!text.isNullOrBlank()) return text

        // InboxStyle인 경우 여러 줄 텍스트 결합
        val textLines = extras.getCharSequenceArray(Notification.EXTRA_TEXT_LINES)
        if (!textLines.isNullOrEmpty()) {
            return textLines.joinToString(" ")
        }

        return ""
    }

    /**
     * Notification.MessagingStyle의 EXTRA_MESSAGES에서
     * 가장 최근 메시지의 텍스트를 추출한다.
     */
    private fun extractFromMessagingStyle(extras: Bundle): String? {
        val messages = extras.getParcelableArray(Notification.EXTRA_MESSAGES)
        if (messages.isNullOrEmpty()) return null

        // 가장 최근 메시지 (마지막 항목)
        val lastMessage = messages.last()
        if (lastMessage is Bundle) {
            return lastMessage.getCharSequence("text")?.toString()
        }

        return null
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification?) {
        // 필요 시 알림 제거 이벤트 처리
    }
}
