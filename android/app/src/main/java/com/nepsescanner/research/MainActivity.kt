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
    private var mobileSession: MobileSession? = null
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
        val names = listOf("Market", "Historical chart", "Research scanner", "Broker flow", "Portfolio (offline)", "Private account", "Portfolio (reviewed volume)")
        names.forEachIndexed { i, name ->
            tabs.addView(RadioButton(this).apply { id = i + 100; text = name; setTextColor(Color.WHITE) })
        }
        val symbol = input("Stock symbol")
        val start = input("Start YYYY-MM-DD")
        val end = input("End YYYY-MM-DD")
        val portfolioInput = EditText(this).apply {
            hint = "SYMBOL,quantity,cost,price,YYYY-MM-DD,sector,avg daily qty (optional)"
            setTextColor(Color.WHITE); setHintTextColor(Color.LTGRAY)
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE
            minLines = 4; maxLines = 10
            visibility = View.GONE
            filters = arrayOf(android.text.InputFilter.LengthFilter(60000))
            importantForAutofill = View.IMPORTANT_FOR_AUTOFILL_NO
            isSaveEnabled = false
        }
        val portfolioNote = label("Manual prices only, one holding per line. No data is sent or saved. Fees and taxes excluded.").apply { visibility = View.GONE }
        val button = Button(this).apply { text = "Load research" }
        val status = label("Select a research workspace.")
        val accountPanel = LinearLayout(this).apply { orientation=LinearLayout.VERTICAL; visibility=View.GONE }
        val accountNote=label("Development session only. Obtain a short-lived token from your trusted HTTPS gateway. Never enter a proxy secret or password here.")
        val sessionToken=input("Gateway-issued access token").apply {
            inputType=android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD
            isSaveEnabled=false; importantForAutofill=View.IMPORTANT_FOR_AUTOFILL_NO
        }
        val connect=Button(this).apply { text="Connect existing session" }
        val logout=Button(this).apply { text="Log out" }
        val watchInput=input("Watchlist symbols, comma-separated").apply { isSaveEnabled=false }
        val watchLoad=Button(this).apply { text="Load watchlist" }
        val watchSave=Button(this).apply { text="Save watchlist"; isEnabled=false }
        val alertSymbol=input("Alert symbol")
        val alertDirection=Spinner(this).apply { adapter=ArrayAdapter(this@MainActivity,android.R.layout.simple_spinner_dropdown_item,listOf("above","below")) }
        val alertThreshold=input("Alert threshold NPR")
        val alertLoad=Button(this).apply { text="Load alerts" }
        val alertAdd=Button(this).apply { text="Add alert rule" }
        val alertRemove=Button(this).apply { text="Delete matching alert rule" }
        val accountStatus=label("Not connected")
        val accountButtons=listOf(connect,logout,watchLoad,watchSave,alertLoad,alertAdd,alertRemove)
        var watchLoaded=false
        var accountBusy=false
        var accountGeneration=0
        fun resetAccount() { mobileSession?.clear(); mobileSession=null; watchLoaded=false; watchInput.text.clear(); sessionToken.text.clear(); accountStatus.text="Not connected"; watchSave.isEnabled=false }
        fun accountAction(action: (ResearchApi) -> String, completed: (String) -> Unit = { accountStatus.text=it }) {
            if(accountBusy) return
            val session=mobileSession ?: run { accountStatus.text="Connect an authorized session first."; return }
            val base=endpoint.text.toString()
            val epoch=accountGeneration
            accountBusy=true; accountButtons.forEach{it.isEnabled=false}
            worker.execute {
                val result=runCatching { action(ResearchApi(base,session)) }
                runOnUiThread {
                    if(!isDestroyed && epoch==accountGeneration) {
                        accountBusy=false; accountButtons.forEach{it.isEnabled=true}
                        if(result.isSuccess) completed(result.getOrThrow()) else { watchLoaded=false; watchInput.text.clear(); accountStatus.text="Account request unavailable. Check session, gateway and inputs." }
                        watchSave.isEnabled=watchLoaded
                    }
                }
            }
        }
        connect.setOnClickListener {
            if(accountBusy)return@setOnClickListener
            val base=endpoint.text.toString(); val token=sessionToken.text.toString()
            resetAccount()
            mobileSession=runCatching { MobileSession(base,token,900) }.getOrElse { accountStatus.text="Invalid session or HTTPS origin"; return@setOnClickListener }
            accountAction({ api -> val r=api.accountSession(); check(r.optBoolean("authenticated",false) && r.optString("mode")=="research_only"); "Authenticated research session" })
        }
        logout.setOnClickListener {
            accountAction({api -> check(api.logout().optBoolean("revoked",false)); "Session revoked" }, { resetAccount(); accountStatus.text=it })
        }
        fun watchText(r: JSONObject): String {
            val rows=r.getJSONArray("symbols")
            return (0 until rows.length()).map { rows.getString(it) }.also { require(it.size<=300 && it.all { x -> x.matches(Regex("[A-Z0-9]{1,20}")) }) }.joinToString(", ")
        }
        watchLoad.setOnClickListener { accountAction({ watchText(it.watchlist()) }, { watchInput.setText(it); watchLoaded=true; accountStatus.text="Watchlist loaded" }) }
        watchSave.setOnClickListener {
            if(!watchLoaded)return@setOnClickListener
            val symbols=watchInput.text.toString().split(",").map{it.trim()}.filter{it.isNotEmpty()}
            accountAction({ watchText(it.saveWatchlist(symbols)) }, {watchInput.setText(it); watchLoaded=true; accountStatus.text="Watchlist saved"})
        }
        fun alertText(r: JSONObject): String {
            check(r.has("delivery_enabled") && !r.getBoolean("delivery_enabled"))
            val rules=r.getJSONArray("rules")
            return (0 until rules.length()).joinToString("\n") { i -> val a=rules.getJSONObject(i); "${a.getString("symbol")} ${a.getString("direction")} NPR ${a.getString("threshold")}" }+"\nNotification delivery disabled."
        }
        alertLoad.setOnClickListener { accountAction({alertText(it.alerts())}) }
        fun changeAlert(remove:Boolean) {
            val stock=alertSymbol.text.toString(); val dir=alertDirection.selectedItem.toString(); val price=alertThreshold.text.toString()
            accountAction({alertText(it.changeAlert(stock,dir,price,remove))})
        }
        alertAdd.setOnClickListener { changeAlert(false) }; alertRemove.setOnClickListener { changeAlert(true) }
        listOf(accountNote,sessionToken,connect,logout,watchInput,watchLoad,watchSave,alertSymbol,alertDirection,alertThreshold,alertLoad,alertAdd,alertRemove,accountStatus).forEach{accountPanel.addView(it)}

        val chart = CandleView(this).apply { visibility = View.GONE }
        val chartControls = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; visibility = View.GONE }
        val chartRange = label("")
        val frame = Spinner(this).apply { adapter = ArrayAdapter(this@MainActivity, android.R.layout.simple_spinner_dropdown_item, listOf("Daily", "Weekly", "Monthly", "Quarterly", "Yearly")) }
        val earlier = Button(this).apply { text = "Earlier candles" }
        val later = Button(this).apply { text = "Later candles" }
        val zoomIn = Button(this).apply { text = "Zoom in" }
        val zoomOut = Button(this).apply { text = "Zoom out" }
        val latest = Button(this).apply { text = "Latest candles" }
        val expand = Button(this).apply { text = "Expand chart" }
        var expanded = false
        expand.setOnClickListener { expanded = !expanded; chart.layoutParams = chart.layoutParams.apply { height = ((if(expanded) 560 else 280)*resources.displayMetrics.density).toInt() }; expand.text = if(expanded) "Reduce chart" else "Expand chart" }
        val fullscreen = Button(this).apply { text = "Full-screen chart" }
        var activeChartDialog: android.app.Dialog? = null
        fullscreen.setOnClickListener {
            if (activeChartDialog?.isShowing == true) return@setOnClickListener
            val dialog = android.app.Dialog(this, android.R.style.Theme_Material_NoActionBar)
            val panel = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setBackgroundColor(Color.rgb(11,17,27)) }
            val range = label(chart.rangeLabel())
            val largeChart = CandleView(this).apply { copyViewportFrom(chart) }
            val close = Button(this).apply { text = "Exit full screen" }
            largeChart.onRangeChanged = { range.text = largeChart.rangeLabel() }
            panel.addView(close)
            panel.addView(range)
            panel.addView(largeChart, LinearLayout.LayoutParams(-1,0,1f))
            close.setOnClickListener { dialog.dismiss() }
            dialog.setContentView(panel)
            dialog.setOnDismissListener { chart.copyViewportFrom(largeChart); updateChartRange(chartRange,chart); activeChartDialog = null }
            activeChartDialog = dialog
            dialog.show()
            dialog.window?.setLayout(-1,-1)
            dialog.window?.decorView?.systemUiVisibility = (View.SYSTEM_UI_FLAG_FULLSCREEN or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY)
        }
        listOf(frame,chartRange,earlier,later,zoomIn,zoomOut,latest,expand,fullscreen).forEach { chartControls.addView(it) }
        var fullHistory = emptyList<Candle>()
        fun updateRange() { chartRange.text = chart.rangeLabel() }
        chart.onRangeChanged = { updateRange() }
        fun changeFrame() { chart.replace(aggregateObserved(fullHistory, frame.selectedItemPosition)); updateRange() }
        frame.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) { changeFrame() }
            override fun onNothingSelected(parent: AdapterView<*>?) {} 
        }
        earlier.setOnClickListener { chart.pan(-1); updateRange() }
        later.setOnClickListener { chart.pan(1); updateRange() }
        zoomIn.setOnClickListener { chart.zoom(0.5); updateRange() }
        zoomOut.setOnClickListener { chart.zoom(2.0); updateRange() }
        latest.setOnClickListener { chart.latest(); updateRange() }
        listOf(title,note,endpoint,tabs,symbol,start,end,portfolioNote,portfolioInput,accountPanel,button,status,chartControls).forEach { root.addView(it) }
        root.addView(chart, LinearLayout.LayoutParams(-1, (280 * resources.displayMetrics.density).toInt()))
        setContentView(ScrollView(this).apply { addView(root) })
        tabs.setOnCheckedChangeListener { _, checked ->
            generation++
            val mode = checked - 100
            symbol.visibility = if (mode in 1..3) View.VISIBLE else View.GONE
            endpoint.visibility = if(mode==4) View.GONE else View.VISIBLE
            portfolioInput.visibility = if(mode==4 || mode==6) View.VISIBLE else View.GONE
            portfolioNote.visibility = portfolioInput.visibility
            portfolioNote.text = if(mode==6) "Manual valuation. Only symbol and price date are sent to your research API for reviewed volume. Manual volume is ignored." else "Manual prices only, one holding per line. No data is sent or saved. Fees and taxes excluded."
            button.text = if(mode==4) "Calculate offline" else if(mode==6) "Load reviewed liquidity" else "Load research"
            accountPanel.visibility=if(mode==5) View.VISIBLE else View.GONE
            button.visibility=if(mode==5) View.GONE else View.VISIBLE
            start.visibility = if (mode == 3) View.VISIBLE else View.GONE
            end.visibility = start.visibility
            chart.visibility = View.GONE
            fullHistory = emptyList()
            chartControls.visibility = View.GONE
            chart.replace(emptyList())
            status.text = "Ready • " + names.getOrElse(mode) { "Research" }
            button.isEnabled = true
        }
        tabs.check(100)
        button.setOnClickListener {
            val token = ++generation
            val mode = tabs.checkedRadioButtonId - 100
            if (mode == 4 || mode == 6) {
                val parsed = runCatching {
                    val lines=portfolioInput.text.toString().lines().filter { it.isNotBlank() }
                    require(lines.size in 1..300)
                    val holdings=lines.map { line ->
                        val a=line.split(",").map { it.trim() }
                        require(a.size in 5..7)
                        val date=LocalDate.parse(a[4])
                        require(date.toString()==a[4] && !date.isAfter(LocalDate.now(java.time.ZoneId.of("Asia/Kathmandu"))))
                        Holding(a[0].uppercase(java.util.Locale.ROOT),a[1].toLong(),java.math.BigDecimal(a[2]),java.math.BigDecimal(a[3]),date,a.getOrNull(5)?.takeIf { it.isNotBlank() },a.getOrNull(6)?.takeIf { it.isNotBlank() }?.let { java.math.BigDecimal(it) })
                    }
                    PortfolioMath.calculate(holdings)
                    holdings
                }
                val holdings=parsed.getOrElse { status.text="Invalid holdings. Check dates, symbols, quantities and prices."; return@setOnClickListener }
                if(mode==6) {
                    if(holdings.size>30) { status.text="Reviewed liquidity: maximum 30 holdings per request."; return@setOnClickListener }
                    val base=endpoint.text.toString()
                    val session=mobileSession
                    button.isEnabled=false
                    status.text="Loading reviewed volume…"
                    worker.execute {
                        val result=runCatching {
                            val api=ResearchApi(base,session)
                            val evidence=holdings.associate { h -> h.symbol to runCatching { api.portfolioVolume(h.symbol,h.priceDate) }.getOrDefault(emptyList()) }
                            val admitted=applyVerifiedLiquidityEvidence(holdings,evidence)
                            val risk=exposureRisk(admitted,java.math.BigDecimal("10"))
                            "Manual valuation; reviewed historical volume only; 10% assumed participation; no execution guarantee.\n"+admitted.zip(risk.liquidity).joinToString("\n") { (h,estimate) -> "${h.symbol} | As of ${h.priceDate} | ADV ${h.averageDailyQuantity ?: "Unavailable"} | Liquidation sessions ${estimate.estimatedSessions ?: "Unknown"}" }
                        }
                        runOnUiThread { if(!isDestroyed && token==generation) { button.isEnabled=true; status.text=result.getOrElse { "Reviewed liquidity unavailable" } } }
                    }
                    return@setOnClickListener
                }
                status.text=runCatching {
                    val p=PortfolioMath.calculate(holdings)
                    val risk=exposureRisk(holdings,java.math.BigDecimal("10"))
                    fun money(v: java.math.BigDecimal)=v.setScale(2,java.math.RoundingMode.HALF_UP).toPlainString()
                    "Manual valuation • not live • NPR\nCost: ${money(p.cost)}\nValue: ${money(p.value)}\nUnrealized P/L: ${money(p.pnl)}\n\nHoldings:\n"+p.holdings.joinToString("\n") {
                        "${it.symbol} | Value ${money(it.value)} | P/L ${money(it.pnl)} | Weight ${it.weightPct}% | Price date ${it.priceDate}"
                    }+"\n\nSector weights (user supplied):\n"+p.sectorWeights.entries.sortedByDescending { it.value }.joinToString("\n") { "${it.key}: ${it.value}%" }+"\n\nLargest stock: ${risk.largestStockPct}% | Top three: ${risk.topThreeStockPct}%\nLargest classified sector: ${risk.largestSectorPct ?: "Unknown"}% | Unclassified: ${risk.unclassifiedPct}%\nEstimated liquidation sessions (manual average volume, assumed 10% participation, no execution guarantee):\n"+risk.liquidity.joinToString("\n") { "${it.symbol}: ${it.estimatedSessions ?: "Unknown"}" }+"\nFees and taxes excluded."
                }.getOrElse { "Invalid holdings. Check dates, symbols, duplicate entries, quantities and positive prices." }
                return@setOnClickListener
            }
            val base = endpoint.text.toString()
            val stock = symbol.text.toString().trim().uppercase(java.util.Locale.ROOT)
            val first = start.text.toString().trim()
            val last = end.text.toString().trim()
            button.isEnabled = false
            chart.visibility = View.GONE
            fullHistory = emptyList()
            chartControls.visibility = View.GONE
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
                        fullHistory = result.candles
                        changeFrame()
                        chartControls.visibility = if (fullHistory.isEmpty()) View.GONE else View.VISIBLE
                        chart.visibility = if (result.candles.isEmpty()) View.GONE else View.VISIBLE
                        button.isEnabled = true
                    }
                }
            }
        }
    }
    override fun onDestroy() { generation++; mobileSession?.clear(); worker.shutdownNow(); super.onDestroy() }
}

private fun updateChartRange(label: TextView, chart: CandleView) { label.text = chart.rangeLabel() }

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
    }.sortedBy { it.date }
}

private fun aggregateObserved(rows: List<Candle>, frame: Int): List<Candle> {
    if (frame == 0) return rows
    val iso = java.time.temporal.WeekFields.ISO
    return rows.groupBy { r ->
        val d = LocalDate.parse(r.date)
        when(frame) {
            1 -> "${d.get(iso.weekBasedYear())}-${d.get(iso.weekOfWeekBasedYear())}"
            2 -> "${d.year}-${d.monthValue}"
            3 -> "${d.year}-${(d.monthValue-1)/3}"
            4 -> "${d.year}"
            else -> r.date
        }
    }.values.map { group -> Candle(group.last().date,group.first().open,group.maxOf{it.high},group.minOf{it.low},group.last().close) }
}

private class CandleView(context: android.content.Context): View(context) {
    private var rows: List<Candle> = emptyList()
    private val paint=Paint(Paint.ANTI_ALIAS_FLAG)
    private var window = 80
    private var end = 0
    var onRangeChanged: (() -> Unit)? = null
    private var dragX = 0f
    private val scaleDetector = android.view.ScaleGestureDetector(context, object : android.view.ScaleGestureDetector.SimpleOnScaleGestureListener() {
        override fun onScale(detector: android.view.ScaleGestureDetector): Boolean { zoom(1.0/detector.scaleFactor); onRangeChanged?.invoke(); return true }
    })
    override fun onTouchEvent(event: android.view.MotionEvent): Boolean {
        if(rows.isEmpty()) return false
        scaleDetector.onTouchEvent(event)
        when(event.actionMasked) {
            android.view.MotionEvent.ACTION_DOWN -> { dragX=event.x; parent.requestDisallowInterceptTouchEvent(true) }
            android.view.MotionEvent.ACTION_POINTER_UP -> { dragX=event.getX(if(event.actionIndex==0) 1 else 0) }
            android.view.MotionEvent.ACTION_MOVE -> if(!scaleDetector.isInProgress && event.pointerCount==1) { val step=(width-74f)/maxOf(1,visible().size); if(step>0){val shift=((event.x-dragX)/step).toInt(); if(shift!=0){end=(end-shift).coerceIn(minOf(window,rows.size),rows.size); dragX+=shift*step; invalidate(); onRangeChanged?.invoke()}} }
            android.view.MotionEvent.ACTION_UP, android.view.MotionEvent.ACTION_CANCEL -> { parent.requestDisallowInterceptTouchEvent(false); if(event.actionMasked==android.view.MotionEvent.ACTION_UP) performClick() }
        }
        return true
    }
    override fun performClick(): Boolean { super.performClick(); return true }
    fun copyViewportFrom(other: CandleView) { rows=other.rows; window=other.window; end=other.end; invalidate() }
    fun replace(data: List<Candle>) { rows=data; end=data.size; window=80; invalidate() }
    fun pan(direction: Int) { if(rows.isNotEmpty()){ end=(end+direction*maxOf(1,window/2)).coerceIn(minOf(window,rows.size),rows.size); invalidate() } }
    fun zoom(factor: Double) { if(rows.isNotEmpty()){ window=(window*factor).toInt().coerceIn(5,500); end=end.coerceIn(minOf(window,rows.size),rows.size); invalidate() } }
    fun latest() { end=rows.size; invalidate() }
    private fun visible() = rows.subList(maxOf(0,end-window),end)
    fun rangeLabel(): String { val v=visible(); return if(v.isEmpty()) "No observations" else "${v.first().date} to ${v.last().date} | ${v.size} visible / ${rows.size} available (observed periods; completeness not verified)" }
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if(rows.isEmpty() || width<100 || height<100) return
        val shown=visible()
        if(shown.isEmpty()) return
        val hi=shown.maxOf { it.high }; val lo=shown.minOf { it.low }
        val span=(hi-lo).takeIf { it>0 } ?: hi*0.01
        val left=8f; val right=width-66f; val top=16f; val bottom=height-30f
        val step=(right-left)/shown.size
        fun y(p:Double)= (bottom-(p-lo)/span*(bottom-top)).toFloat()
        paint.color=Color.LTGRAY; paint.textSize=12f
        canvas.drawText("%.2f".format(java.util.Locale.ROOT,hi),right+2,top+10,paint)
        canvas.drawText("%.2f".format(java.util.Locale.ROOT,lo),right+2,bottom,paint)
        shown.forEachIndexed { i,r ->
            val x=left+(i+0.5f)*step
            paint.color=if(r.close>=r.open) Color.rgb(69,214,160) else Color.rgb(239,104,116)
            canvas.drawLine(x,y(r.high),x,y(r.low),paint)
            val a=minOf(y(r.open),y(r.close)); val b=maxOf(y(r.open),y(r.close))
            canvas.drawRect(x-step*0.3f,a,x+step*0.3f,maxOf(a+1,b),paint)
        }
    }
}
