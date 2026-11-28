package com.nepsescanner.research

import org.junit.Test
import org.junit.Assert.*
import java.math.BigDecimal
import java.time.LocalDate

class PortfolioMathTest {
    private fun h(symbol: String, quantity: Long, cost: String, price: String, sector: String? = null) =
        Holding(symbol, quantity, BigDecimal(cost), BigDecimal(price), LocalDate.parse("2026-11-20"), sector)
    private fun eq(expected: String, actual: BigDecimal) { assertEquals(0, BigDecimal(expected).compareTo(actual)) }
    @Test fun valuationAndConcentration() {
        val p = PortfolioMath.calculate(listOf(h("AAA",10,"100","120","Bank"),h("BBB",20,"50","40")))
        eq("2000",p.cost); eq("2000",p.value); eq("0",p.pnl)
        eq("60",p.holdings.first().weightPct)
        eq("60",p.sectorWeights.getValue("Bank"))
        eq("40",p.sectorWeights.getValue("UNCLASSIFIED"))
        eq("200",p.holdings.first().pnl); eq("-200",p.holdings.last().pnl)
    }
    @Test fun decimalPrecision() {
        val p=PortfolioMath.calculate(listOf(h("AAA",3,"100.1234","101.1234")))
        eq("300.3702",p.cost); eq("303.3702",p.value); eq("3",p.pnl)
    }
    @Test fun invalidHoldings() {
        val good=h("AAA",1,"100","100")
        for(rows in listOf(emptyList(),listOf(good,good),listOf(good.copy(quantity=0)),
            listOf(good.copy(observedPrice=BigDecimal("-1"))),listOf(good.copy(symbol="bad!")))) {
            assertThrows(IllegalArgumentException::class.java) { PortfolioMath.calculate(rows) }
        }
    }

    @Test fun liquidityAndExposure() {
        val a=h("AAA",1000,"10","12","Bank").copy(averageDailyQuantity=BigDecimal("2000"))
        val b=h("BBB",1000,"10","8")
        val risk=exposureRisk(listOf(a,b),BigDecimal("10"))
        eq("60",risk.largestStockPct)
        eq("100",risk.topThreeStockPct)
        eq("40",risk.unclassifiedPct)
        eq("5",risk.liquidity.first().estimatedSessions!!)
        assertNull(risk.liquidity.last().estimatedSessions)
        assertThrows(IllegalArgumentException::class.java) { exposureRisk(listOf(a),BigDecimal.ZERO) }
    }
}
