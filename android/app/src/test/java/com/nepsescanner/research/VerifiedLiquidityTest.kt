package com.nepsescanner.research

import org.junit.Test
import org.junit.Assert.*
import java.time.LocalDate
import java.math.BigDecimal

class VerifiedLiquidityTest {
    private fun rows(n:Int=20)= (0 until n).map { i ->
        DatedVolumeEvidence("AAA",LocalDate.parse("2026-01-01").plusDays(i.toLong()),1000L,
            "provider-a","a".repeat(64),"verified","final")
    }
    @Test fun admitsOnlyCompleteVerifiedDatedWindow() {
        assertEquals(1000,eligibleAverageDailyVolume("AAA",rows())!!.toInt())
        assertNull(eligibleAverageDailyVolume("AAA",rows(19)))
        assertNull(eligibleAverageDailyVolume("AAA",rows().dropLast(1)+rows().last().copy(finalityStatus="provisional")))
        assertNull(eligibleAverageDailyVolume("AAA",rows().dropLast(1)+rows().last().copy(sourceValidationStatus="unverified")))
        assertNull(eligibleAverageDailyVolume("AAA",rows().dropLast(1)+rows().last().copy(payloadSha256="bad")))
    }
    @Test fun rejectsDuplicateDatesAndNegativeQuantity() {
        val r=rows()
        assertNull(eligibleAverageDailyVolume("AAA",r.dropLast(1)+r.first()))
        assertNull(eligibleAverageDailyVolume("AAA",r.dropLast(1)+r.last().copy(quantity=-1)))
    }

    @Test fun attachesOnlyAdmittedVolumeToMatchingHolding() {
        val holdings=listOf(Holding("AAA",100,"10".toBigDecimal(),"11".toBigDecimal(),
            LocalDate.parse("2026-01-20"),"BANK",BigDecimal("999")))
        val admitted=applyVerifiedLiquidityEvidence(holdings,mapOf("AAA" to rows()))
        assertEquals(1000,admitted.single().averageDailyQuantity!!.toInt())
        val rejected=applyVerifiedLiquidityEvidence(holdings,mapOf("AAA" to rows().dropLast(1)))
        assertNull(rejected.single().averageDailyQuantity)
    }
}
