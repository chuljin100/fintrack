package com.fintrack.app.data.model

data class TransactionData(
    val amount: Int,
    val vendor: String,
    val timestamp: Long,
    val bank: String
)
