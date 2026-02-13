package com.fintrack.app.data.remote

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface FinTrackApi {

    @POST("transactions")
    suspend fun createTransaction(@Body request: TransactionRequest): TransactionResponse

    @GET("budget/daily")
    suspend fun getDailyBudget(@Query("user_id") userId: String): DailyBudgetResponse

    @POST("plan/forecast")
    suspend fun getForecast(@Body request: ForecastRequest): ForecastResponse
}

data class TransactionRequest(
    val user_id: String,
    val amount: Int,
    val vendor: String,
    val raw_text: String,
    val transaction_date: String
)

data class TransactionResponse(
    val id: Int,
    val amount: Int,
    val vendor: String,
    val category: String?
)

data class DailyBudgetResponse(
    val daily_budget: Int,
    val remaining_this_month: Int,
    val days_left: Int
)

data class ForecastRequest(
    val user_id: String,
    val target_amount: Int,
    val months: Int
)

data class ForecastResponse(
    val achievable: Boolean,
    val monthly_saving_avg: Int,
    val projected_total: Int,
    val deficit: Int
)
