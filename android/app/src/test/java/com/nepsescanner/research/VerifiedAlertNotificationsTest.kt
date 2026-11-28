package com.nepsescanner.research

import org.junit.Test
import org.junit.Assert.*

class VerifiedAlertNotificationsTest {
    @Test fun rejectsUnverifiedOrMalformedEventsBeforeNotificationAccess() {
        val base=mapOf("symbol" to "AAA","session" to "2026-11-20",
            "source_payload_sha256" to "a".repeat(64),
            "source_validation_status" to "verified","finality_status" to "final")
        assertFalse(VerifiedAlertNotifications.deliver(null,base.toMutableMap().apply { put("finality_status","provisional") }))
        assertFalse(VerifiedAlertNotifications.deliver(null,base.toMutableMap().apply { put("source_validation_status","unverified") }))
        assertFalse(VerifiedAlertNotifications.deliver(null,base.toMutableMap().apply { put("source_payload_sha256","bad") }))
        assertFalse(VerifiedAlertNotifications.deliver(null,base.toMutableMap().apply { put("session","not-a-date") }))
    }
}
