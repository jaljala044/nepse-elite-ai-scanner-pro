package com.nepsescanner.research

import android.app.Activity
import android.os.Bundle
import android.widget.*
import android.graphics.Color
import android.view.View
import android.graphics.Canvas
import android.graphics.Paint
import java.time.LocalDate
import java.util.concurrent.Executors
import org.json.JSONObject
import org.json.JSONArray

class MainActivity : Activity() {
    private val worker = Executors.newSingleThreadExecutor()
    private var generation = 0
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 48, 24, 24)
            setBackgroundColor(Color.rgb(11,17,27))
        }
        fun label(value: String, size: Float = 16f) = TextView(this).apply {
            text = value; textSize = size; setTextColor(Color.WHITE)
        }
        fun input(placeholder: String) = EditText(this).apply {
            hint = placeholder; setSingleLine(true); setTextColor(Color.WHITE); setHintTextColor(Color.LTGRAY)
        }
        val title = label("NEPSE Scanner", 26f)
        val note = label("Research only • No verified live feed • AI recommendations OFF")
        val endpoint = input("HTTPS research API origin").apply { inputType = 17 }
        val tabs = RadioGroup(this).apply { orientation = RadioGroup.VERTICAL }
        val names = listOf("Market", "Historical chart", "Research scanner", "Broker flow")
        names.forEachIndexed { i, name ->
            tabs.addView(RadioButton(this).apply { id = i + 100; text = name; setTextColor(Color.WHITE) })
        }
        val symbol = input("Stock symbol")
        val start = input("Start YYYY-MM-DD")
        val end = input("End YYYY-MM-DD")
        val button = Button(this).apply { text = "Load research" }
        val status = label("Select a research workspace.")
        val chart = CandleView(this).apply { visibility = View.GONE }
        listOf(title,note,endpoint,tabs,symbol,start,end,button,status).forEach { root.addView(it) }
        root.addView(chart, LinearLayout.LayoutParams(-1, (280 * resources.displayMetrics.density).toInt()))
        setContentView(ScrollView(this).apply { addView(root) })
        tabs.setOnCheckedChangeListener { _, checked ->
            generation++
            val mode = checked - 100
            symbol.visibility = if (mode == 0) View.GONE else View.VISIBLE
            start.visibility = if (mode == 3) View.VISIBLE else View.GONE
            end.visibility = start.visibility
            chart.visibility = View.GONE
            chart.replace(emptyList())
            status.text = "Ready • " + names.getOrElse(mode) { "Research" }
            button.isEnabled = true
        }
        tabs.check(100)
        button.setOnClickListener {
            val token = ++generation
            val mode = tabs.checkedRadioButtonId - 100
            val base = endpoint.text.toString()
            val stock = symbol.text.toString().trim().uppercase(java.util.Locale.ROOT)
            val first = start.text.toString().trim()
            val last = end.text.toString().trim()
            button.isEnabled = false
            chart.visibility = View.GONE
            chart.replace(emptyList())
            status.text = "Checking research API…"
            worker.execute {
                val result = runCatching {
                    val api = ResearchApi(base)
                    val ready = api.readiness()
                    check(ready.optString("mode") == "research_only")
                    check(ready.has("production_recommendations_enabled") && !ready.getBoolean("production_recommendations_enabled"))
                    when (mode) {
                        0 -> {
                            val h = api.marketHealth()
                            ScreenResult("Market evidence: ${h.optString("status","unknown")}\nDecision session: ${h.optString("decision_session","unknown")}")
                        }
                        1 -> {
                            val h = api.history(stock)
                            check(h.optString("symbol") == stock)
                            val candles = parseCandles(h.getJSONArray("rows"))
                            check(candles.isNotEmpty()) { "No historical observations" }
                            ScreenResult("$stock • observed daily data, not independently certified\n${candles.first().date} to ${candles.last().date}\nLatest close: ${candles.last().close}",candles)
                        }
                        2 -> {
                            val r = api.scan(stock)
                            check(r.optString("mode") == "research_only")
                            val rows = r.getJSONArray("results")
                            val lines = (0 until rows.length()).map { i ->
                                val row = rows.getJSONObject(i)
                                check(row.optString("symbol") == stock)
                                val eligibility = row.optJSONObject("eligibility")
                                "${row.optString("symbol")} • ${row.optString("status","unknown")}\nEvidence eligible: ${eligibility?.optBoolean("eligible",false) ?: false}\nReasons: ${eligibility?.optJSONArray("reasons") ?: "Unavailable"}"
                            }
                            ScreenResult(lines.joinToString("\n\n").ifBlank { "No research results" } + "\nAI recommendations OFF")
                        }
                        3 -> {
                            val r = api.brokers(stock,first,last)
                            if (r.optString("status") != "research_only") ScreenResult("Broker evidence unavailable: ${r.optString("reason","unknown")}")
                            else {
                                check(r.optString("symbol")==stock && r.optString("start")==first && r.optString("end")==last)
                                val rows = r.getJSONArray("brokers")
                                val lines = (0 until rows.length()).map { i ->
                                    val row=rows.getJSONObject(i)
                                    "Broker ${row.optString("broker_code")} | Buy ${row.optString("buy_qty")} | Sell ${row.optString("sell_qty")} | Net qty ${row.optString("net_qty")} | Net NPR ${row.optString("net_amount")}"
                                }
                                ScreenResult("$stock • $first to $last\n"+lines.joinToString("\n")+"\nBroker flow does not prove beneficial ownership or accumulation.")
                            }
                        }
                        else -> error("Unknown workspace")
                    }
                }.getOrElse { ScreenResult("Research unavailable. Check inputs, HTTPS origin and authorized access.") }
                runOnUiThread {
                    if (!isDestroyed && generation == token) {
                        status.text = result.text
                        chart.replace(result.candles)
                        chart.visibility = if (result.candles.isEmpty()) View.GONE else View.VISIBLE
                        button.isEnabled = true
                    }
                }
            }
        }
    }
    override fun onDestroy() { generation++; worker.shutdownNow(); super.onDestroy() }
}

private data class ScreenResult(val text: String, val candles: List<Candle> = emptyList())
private data class Candle(val date: String,val open: Double,val high: Double,val low: Double,val close: Double)

private fun parseCandles(rows: JSONArray): List<Candle> {
    val seen=mutableSetOf<String>()
    require(rows.length() <= 20000)
    return (0 until rows.length()).map { i ->
        val r=rows.getJSONObject(i)
        val date=r.getString("date")
        require(LocalDate.parse(date).toString()==date && seen.add(date))
        val o=r.getDouble("open"); val h=r.getDouble("high"); val l=r.getDouble("low"); val c=r.getDouble("close")
        require(listOf(o,h,l,c).all { it.isFinite() && it>0 } && h>=maxOf(o,c,l) && l<=minOf(o,c))
        Candle(date,o,h,l,c)
    }.sortedBy { it.date }.takeLast(80)
}

private class CandleView(context: android.content.Context): View(context) {
    private var rows: List<Candle> = emptyList()
    private val paint=Paint(Paint.ANTI_ALIAS_FLAG)
    fun replace(data: List<Candle>) { rows=data; invalidate(); contentDescription=if(data.isEmpty()) "No historical chart" else "Historical daily candlestick chart, ${data.size} observations" }
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if(rows.isEmpty() || width<100 || height<100) return
        val hi=rows.maxOf { it.high }; val lo=rows.minOf { it.low }
        val span=(hi-lo).takeIf { it>0 } ?: hi*0.01
        val left=8f; val right=width-66f; val top=16f; val bottom=height-30f
        val step=(right-left)/rows.size
        fun y(p:Double)= (bottom-(p-lo)/span*(bottom-top)).toFloat()
        paint.color=Color.LTGRAY; paint.textSize=12f
        canvas.drawText("%.2f".format(java.util.Locale.ROOT,hi),right+2,top+10,paint)
        canvas.drawText("%.2f".format(java.util.Locale.ROOT,lo),right+2,bottom,paint)
        rows.forEachIndexed { i,r ->
            val x=left+(i+0.5f)*step
            paint.color=if(r.close>=r.open) Color.rgb(69,214,160) else Color.rgb(239,104,116)
            canvas.drawLine(x,y(r.high),x,y(r.low),paint)
            val a=minOf(y(r.open),y(r.close)); val b=maxOf(y(r.open),y(r.close))
            canvas.drawRect(x-step*0.3f,a,x+step*0.3f,maxOf(a+1,b),paint)
        }
    }
}
