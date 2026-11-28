package com.nepsescanner.research

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat

internal object VerifiedAlertNotifications {
    const val CHANNEL_ID="verified_market_alerts"
    fun createChannel(context: Context) {
        if(Build.VERSION.SDK_INT>=Build.VERSION_CODES.O) {
            val manager=context.getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(NotificationChannel(CHANNEL_ID,"Verified market alerts",NotificationManager.IMPORTANCE_DEFAULT).apply {
                description="Alerts based only on final, source-verified market observations"
            })
        }
    }
    fun deliver(context: Context, event: Map<String,String>): Boolean {
        val symbol=event["symbol"] ?: return false
        val session=event["session"] ?: return false
        val digest=event["source_payload_sha256"] ?: return false
        if(!symbol.matches(Regex("[A-Z0-9]{1,20}")) ||
            runCatching { java.time.LocalDate.parse(session).toString()==session }.getOrDefault(false).not() ||
            !digest.matches(Regex("[a-fA-F0-9]{64}")) ||
            event["source_validation_status"]!="verified" || event["finality_status"]!="final") return false
        if(Build.VERSION.SDK_INT>=33 && context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED) return false
        createChannel(context)
        val id=(symbol+session).hashCode()
        return try {
            NotificationManagerCompat.from(context).notify(id,
                NotificationCompat.Builder(context,CHANNEL_ID)
                    .setSmallIcon(android.R.drawable.ic_dialog_info)
                    .setContentTitle("NEPSE research alert: "+symbol)
                    .setContentText(event["message"]?.take(160) ?: "A verified market threshold was reached")
                    .setAutoCancel(true).build())
            true
        } catch (_: SecurityException) { false }
    }
}
