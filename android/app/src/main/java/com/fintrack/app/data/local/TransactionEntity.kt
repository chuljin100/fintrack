package com.fintrack.app.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "transactions")
data class TransactionEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val amount: Int,
    val vendor: String,
    val bank: String,
    val rawText: String = "",
    val category: String? = null,
    val synced: Boolean = false,
    val transactionDate: Long,
    val createdAt: Long = System.currentTimeMillis()
)
