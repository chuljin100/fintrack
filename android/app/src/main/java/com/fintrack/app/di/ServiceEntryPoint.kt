package com.fintrack.app.di

import com.fintrack.app.data.TransactionRepository
import dagger.hilt.EntryPoint
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

/**
 * NotificationListenerService는 @AndroidEntryPoint를 지원하지 않으므로
 * EntryPointAccessors를 통해 의존성에 접근한다.
 */
@EntryPoint
@InstallIn(SingletonComponent::class)
interface ServiceEntryPoint {
    fun transactionRepository(): TransactionRepository
}
