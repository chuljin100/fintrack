package com.fintrack.app.data

import android.util.Log
import com.fintrack.app.data.local.TransactionDao
import com.fintrack.app.data.local.TransactionEntity
import com.fintrack.app.data.model.TransactionData
import com.fintrack.app.data.remote.FinTrackApi
import com.fintrack.app.data.remote.TransactionRequest
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class TransactionRepository @Inject constructor(
    private val dao: TransactionDao,
    private val api: FinTrackApi
) {
    companion object {
        private const val TAG = "TransactionRepository"
        private const val USER_ID = "default_user" // TODO: 실제 사용자 인증 연동
    }

    private val dateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())

    /**
     * 거래를 Room에 저장한 뒤, 서버 전송을 시도한다.
     * 서버 전송 실패 시 synced=false로 남겨두고 나중에 재시도.
     */
    suspend fun saveAndSync(data: TransactionData, rawText: String) {
        // 1. Room에 먼저 저장 (오프라인 우선)
        val entity = TransactionEntity(
            amount = data.amount,
            vendor = data.vendor,
            bank = data.bank,
            rawText = rawText,
            transactionDate = data.timestamp,
            synced = false
        )
        val localId = dao.insert(entity)
        Log.d(TAG, "Room 저장 완료: id=$localId, ${data.vendor} ${data.amount}원")

        // 2. 서버로 전송 시도
        try {
            val request = TransactionRequest(
                user_id = USER_ID,
                amount = data.amount,
                vendor = data.vendor,
                raw_text = rawText,
                transaction_date = dateFormat.format(Date(data.timestamp))
            )
            val response = api.createTransaction(request)
            dao.markSynced(localId)
            Log.i(TAG, "서버 전송 성공: id=${response.id}, 카테고리=${response.category}")
        } catch (e: Exception) {
            Log.w(TAG, "서버 전송 실패 (나중에 재시도): ${e.message}")
        }
    }

    /**
     * 미전송 거래를 일괄 전송한다. (앱 시작 시 또는 네트워크 복구 시 호출)
     */
    suspend fun syncPending() {
        val unsynced = dao.getUnsynced()
        if (unsynced.isEmpty()) return

        Log.d(TAG, "미전송 거래 ${unsynced.size}건 동기화 시작")
        for (entity in unsynced) {
            try {
                val request = TransactionRequest(
                    user_id = USER_ID,
                    amount = entity.amount,
                    vendor = entity.vendor,
                    raw_text = entity.rawText,
                    transaction_date = dateFormat.format(Date(entity.transactionDate))
                )
                api.createTransaction(request)
                dao.markSynced(entity.id)
                Log.d(TAG, "동기화 완료: id=${entity.id}")
            } catch (e: Exception) {
                Log.w(TAG, "동기화 실패: id=${entity.id}, ${e.message}")
                break // 네트워크 문제면 나머지도 실패할 가능성 높으므로 중단
            }
        }
    }
}
