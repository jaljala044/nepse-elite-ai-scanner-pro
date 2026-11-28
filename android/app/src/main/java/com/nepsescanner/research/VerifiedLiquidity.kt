package com.nepsescanner.research

import java.math.BigDecimal
import java.time.LocalDate

internal data class DatedVolumeEvidence(
    val symbol: String, val sessionDate: LocalDate, val quantity: Long,
    val sourceId: String, val payloadSha256: String,
    val sourceValidationStatus: String, val finalityStatus: String
)

internal fun eligibleAverageDailyVolume(symbol: String, evidence: List<DatedVolumeEvidence>, requiredSessions: Int = 20): BigDecimal? {
    require(symbol.matches(Regex("[A-Z0-9]{1,20}")) && requiredSessions in 1..252)
    val rows=evidence.filter { it.symbol==symbol }
    if(rows.size!=requiredSessions || rows.map { it.sessionDate }.distinct().size!=requiredSessions) return null
    if(rows.any { it.quantity<0 || it.sourceId.isBlank() ||
        !it.payloadSha256.matches(Regex("[a-fA-F0-9]{64}")) ||
        it.sourceValidationStatus!="verified" || it.finalityStatus!="final" }) return null
    return rows.fold(BigDecimal.ZERO) { total,row -> total.add(BigDecimal.valueOf(row.quantity)) }.divide(BigDecimal.valueOf(requiredSessions.toLong()),4,java.math.RoundingMode.HALF_UP)
}

internal fun applyVerifiedLiquidityEvidence(
    holdings: List<Holding>,
    evidenceBySymbol: Map<String,List<DatedVolumeEvidence>>,
    requiredSessions: Int = 20
): List<Holding> {
    require(holdings.map { it.symbol }.distinct().size==holdings.size)
    return holdings.map { holding ->
        val average=eligibleAverageDailyVolume(holding.symbol,evidenceBySymbol[holding.symbol].orEmpty(),requiredSessions)
        holding.copy(averageDailyQuantity=average)
    }
}
