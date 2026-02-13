package com.fintrack.app.util

import com.fintrack.app.data.model.TransactionData
import java.util.Calendar

/**
 * 한국 금융 앱 알림 텍스트를 파싱하여 TransactionData로 변환하는 유틸리티.
 *
 * 지원 패턴 예시:
 * - "신한카드(1234) 김*수님 15,000원 승인 02/15 13:00 스타벅스강남점"
 * - "KB국민카드 승인 홍길동 4,500원 02/15 12:30 CU편의점"
 * - "토스뱅크 30,000원 입금 (김토스)"
 */
object NotificationParser {

    // 금액 패턴: 콤마 포함 숫자 + "원"
    private val AMOUNT_REGEX = Regex("""([\d,]+)\s*원""")

    // 날짜 패턴: MM/dd 또는 MM.dd (선택적으로 시:분 포함)
    private val DATE_REGEX = Regex("""(\d{1,2})[/.:](\d{1,2})\s+(\d{1,2}):(\d{2})""")
    private val DATE_ONLY_REGEX = Regex("""(\d{1,2})[/.](\d{1,2})""")

    // 제거할 노이즈 패턴
    private val NOISE_PATTERNS = listOf(
        Regex("""[\d,]+\s*원"""),                    // 금액
        Regex("""\d{1,2}[/.]\d{1,2}"""),             // 날짜
        Regex("""\d{1,2}:\d{2}"""),                  // 시간
        Regex("""승인|입금|출금|결제|이체|취소"""),      // 거래 유형 키워드
        Regex("""\(.*?\)"""),                        // 괄호 안 내용 (카드번호, 이름 등)
        Regex("""[가-힣]{1,3}\*[가-힣]님?"""),        // 마스킹된 이름 (김*수님)
        Regex("""[가-힣]{2,4}님"""),                  // 이름+님
        Regex("""\b\d{4}\b"""),                      // 4자리 숫자 (카드번호)
        Regex("""신한카드|KB국민카드|카카오뱅크|토스뱅크|우리카드|하나카드|삼성카드|현대카드|롯데카드|NH카드|BC카드"""),
    )

    fun parse(rawText: String, bank: String): TransactionData? {
        val amount = extractAmount(rawText) ?: return null
        val timestamp = extractTimestamp(rawText)
        val vendor = extractVendor(rawText)

        if (vendor.isBlank()) return null

        return TransactionData(
            amount = amount,
            vendor = vendor.trim(),
            timestamp = timestamp,
            bank = bank
        )
    }

    /** 금액 추출: "15,000원" → 15000 */
    private fun extractAmount(text: String): Int? {
        val match = AMOUNT_REGEX.find(text) ?: return null
        val raw = match.groupValues[1].replace(",", "")
        return raw.toIntOrNull()
    }

    /** 날짜 추출: MM/dd HH:mm → timestamp. 날짜 없으면 현재 시각 반환. */
    private fun extractTimestamp(text: String): Long {
        val cal = Calendar.getInstance()

        // 날짜+시간 패턴 먼저 시도
        val fullMatch = DATE_REGEX.find(text)
        if (fullMatch != null) {
            val month = fullMatch.groupValues[1].toInt()
            val day = fullMatch.groupValues[2].toInt()
            val hour = fullMatch.groupValues[3].toInt()
            val minute = fullMatch.groupValues[4].toInt()
            cal.set(Calendar.MONTH, month - 1)
            cal.set(Calendar.DAY_OF_MONTH, day)
            cal.set(Calendar.HOUR_OF_DAY, hour)
            cal.set(Calendar.MINUTE, minute)
            cal.set(Calendar.SECOND, 0)
            cal.set(Calendar.MILLISECOND, 0)
            return cal.timeInMillis
        }

        // 날짜만 있는 경우
        val dateMatch = DATE_ONLY_REGEX.find(text)
        if (dateMatch != null) {
            val month = dateMatch.groupValues[1].toInt()
            val day = dateMatch.groupValues[2].toInt()
            cal.set(Calendar.MONTH, month - 1)
            cal.set(Calendar.DAY_OF_MONTH, day)
            cal.set(Calendar.HOUR_OF_DAY, 0)
            cal.set(Calendar.MINUTE, 0)
            cal.set(Calendar.SECOND, 0)
            cal.set(Calendar.MILLISECOND, 0)
            return cal.timeInMillis
        }

        // 날짜 정보 없으면 현재 시각
        return System.currentTimeMillis()
    }

    /** 가맹점 추출: 노이즈 제거 후 남은 가장 긴 토큰 */
    private fun extractVendor(text: String): String {
        var cleaned = text

        // 노이즈 패턴 순차 제거
        for (pattern in NOISE_PATTERNS) {
            cleaned = pattern.replace(cleaned, " ")
        }

        // 공백 정리 및 특수문자 제거
        cleaned = cleaned.replace(Regex("""[^\w가-힣\s]"""), " ")
            .replace(Regex("""\s+"""), " ")
            .trim()

        // 남은 토큰 중 가장 긴 것을 가맹점 후보로 선택
        val tokens = cleaned.split(" ").filter { it.length >= 2 }
        return tokens.maxByOrNull { it.length } ?: ""
    }
}
