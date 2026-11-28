package com.nepsescanner.research

import java.math.BigDecimal
import java.math.RoundingMode
import java.time.LocalDate

internal data class Holding(val symbol: String, val quantity: Long, val costPerShare: BigDecimal,
    val observedPrice: BigDecimal, val priceDate: LocalDate, val sector: String?)
internal data class HoldingValue(val symbol: String, val cost: BigDecimal, val value: BigDecimal,
    val pnl: BigDecimal, val weightPct: BigDecimal, val sector: String?, val priceDate: LocalDate)
internal data class PortfolioValue(val cost: BigDecimal, val value: BigDecimal, val pnl: BigDecimal,
    val holdings: List<HoldingValue>, val sectorWeights: Map<String, BigDecimal>)

internal object PortfolioMath {
    private fun percent(part: BigDecimal, total: BigDecimal): BigDecimal =
        if(total.signum()==0) BigDecimal.ZERO else part.multiply(BigDecimal(100)).divide(total, 2, RoundingMode.HALF_UP)
    fun calculate(holdings: List<Holding>): PortfolioValue {
        require(holdings.size in 1..300 && holdings.map { it.symbol }.distinct().size == holdings.size)
        for(h in holdings) {
            require(h.symbol.matches(Regex("[A-Z0-9]{1,20}")) && h.quantity in 1..1000000000L)
            require(listOf(h.costPerShare,h.observedPrice).all { it.signum()>0 && it<=BigDecimal("100000000") && it.scale() in 0..4 })
        }
        val costs=holdings.map { it.costPerShare.multiply(BigDecimal.valueOf(it.quantity)) }
        val values=holdings.map { it.observedPrice.multiply(BigDecimal.valueOf(it.quantity)) }
        val cost=costs.fold(BigDecimal.ZERO, BigDecimal::add)
        val value=values.fold(BigDecimal.ZERO, BigDecimal::add)
        val rows=holdings.mapIndexed { i,h -> HoldingValue(h.symbol,costs[i],values[i],values[i]-costs[i],percent(values[i],value),h.sector,h.priceDate) }
        val sectorWeights=rows.groupBy { it.sector?.trim()?.takeIf(String::isNotBlank) ?: "UNCLASSIFIED" }
            .mapValues { (_,members) -> percent(members.map { it.value }.fold(BigDecimal.ZERO,BigDecimal::add),value) }
        return PortfolioValue(cost,value,value-cost,rows,sectorWeights)
    }
}
