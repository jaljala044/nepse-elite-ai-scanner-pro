package com.nepsescanner.research

import java.net.URI
import javax.net.ssl.HttpsURLConnection
import org.json.JSONObject

class ResearchApi(base: String, private val session: MobileSession? = null) {
    private val origin = URI(base.trim()).also {
        require(it.scheme == "https" && it.host != null && it.userInfo == null &&
            it.query == null && it.fragment == null && (it.path.isNullOrEmpty() || it.path == "/"))
    }
    fun marketHealth(): JSONObject = get("/v1/market-health")
    fun readiness(): JSONObject = get("/v1/research/readiness")
    fun history(symbol: String): JSONObject {
        val key = symbolKey(symbol)
        val rows = org.json.JSONArray()
        var offset = 0
        var snapshot: String? = null
        var total = -1
        do {
            check(!Thread.currentThread().isInterrupted)
            val page = get("/v1/history/"+key+"?limit=500&offset="+offset+(snapshot?.let { "&snapshot="+it } ?: ""))
            check(page.getString("symbol")==key && page.getInt("offset")==offset)
            val digest=page.getString("snapshot")
            check(digest.matches(Regex("[a-f0-9]{64}")) && (snapshot==null || snapshot==digest))
            snapshot=digest
            val count=page.getInt("total")
            check(count in 0..20000 && (total<0 || total==count))
            total=count
            val part=page.getJSONArray("rows")
            check(part.length()<=500 && offset+part.length()<=total)
            for(i in 0 until part.length()) rows.put(part.getJSONObject(i))
            if(page.isNull("next_offset")) { check(rows.length()==total); break }
            val next=page.getInt("next_offset")
            check(next==offset+part.length() && next>offset && next<total)
            offset=next
        } while(true)
        return JSONObject().put("symbol",key).put("rows",rows)
    }
    fun scan(symbol: String): JSONObject = get("/v1/scan", JSONObject().put("symbols",org.json.JSONArray().put(symbolKey(symbol))))
    fun brokers(symbol: String, start: String, end: String): JSONObject {
        require(java.time.LocalDate.parse(start).toString()==start && java.time.LocalDate.parse(end).toString()==end && start<=end)
        return get("/v1/broker/summary/"+symbolKey(symbol)+"?start="+start+"&end="+end)
    }
    private fun symbolKey(symbol: String): String = symbol.trim().uppercase(java.util.Locale.ROOT).also { require(it.matches(Regex("[A-Z0-9]{1,20}"))) }
    internal fun portfolioVolume(symbol: String, asOf: java.time.LocalDate): List<DatedVolumeEvidence> {
        val key=symbolKey(symbol)
        val r=get("/v1/portfolio/volume/"+key+"?as_of="+asOf)
        check(r.getString("symbol")==key && r.getString("as_of")==asOf.toString())
        check(r.has("production_eligible") && !r.getBoolean("production_eligible"))
        if(r.getString("status")=="unavailable") return emptyList()
        check(r.getString("status")=="research_only" && r.getInt("session_count")==20)
        val rows=r.getJSONArray("rows")
        check(rows.length()==20)
        val evidence=(0 until rows.length()).map { i ->
            val row=rows.getJSONObject(i)
            val day=java.time.LocalDate.parse(row.getString("session_date"))
            check(row.getString("symbol")==key && !day.isAfter(asOf))
            val quantity=java.math.BigDecimal(row.getString("quantity")).longValueExact()
            DatedVolumeEvidence(key,day,quantity,row.getString("source_id"),
                row.getString("source_payload_sha256"),row.getString("source_validation_status"),row.getString("finality_status"))
        }
        val computed=checkNotNull(eligibleAverageDailyVolume(key,evidence))
        val reported=java.math.BigDecimal(r.getString("average_daily_quantity"))
        check(computed.compareTo(reported)==0)
        return evidence
    }
    fun accountSession(): JSONObject = get("/v1/account/session")
    fun watchlist(): JSONObject = get("/v1/account/watchlist")
    fun saveWatchlist(symbols: List<String>): JSONObject {
        require(symbols.size<=300)
        return get("/v1/account/watchlist",JSONObject().put("symbols",org.json.JSONArray(symbols.map(::symbolKey).distinct())),"PUT")
    }
    fun alerts(): JSONObject = get("/v1/account/alerts")
    fun changeAlert(symbol: String, direction: String, threshold: String, remove: Boolean): JSONObject {
        require(direction in listOf("above","below") && threshold.matches(Regex("[0-9]{1,9}(\\.[0-9]{1,2})?")))
        return get("/v1/account/alerts",JSONObject().put("symbol",symbolKey(symbol)).put("direction",direction).put("threshold",threshold),if(remove) "DELETE" else "POST")
    }
    fun logout(): JSONObject = get("/v1/account/mobile/logout",JSONObject(),"POST")
    private fun get(path: String, body: JSONObject? = null, method: String = if(body==null) "GET" else "POST"): JSONObject {
        val conn = origin.resolve(path).toURL().openConnection() as HttpsURLConnection
        try {
            conn.instanceFollowRedirects = false
            conn.connectTimeout = 10000
            conn.readTimeout = 10000
            conn.setRequestProperty("Accept", "application/json")
            conn.useCaches = false
            if(session!=null) conn.setRequestProperty("Authorization",session.authorizationFor(origin))
            else check(!path.startsWith("/v1/account/")) { "Authenticated mobile session required" }
            if (body != null) {
                conn.requestMethod = method
                conn.doOutput = true
                conn.setRequestProperty("Content-Type", "application/json")
                conn.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
            if(conn.responseCode==401) session?.clear()
            check(conn.responseCode == 200) { "Research API unavailable (HTTP ${conn.responseCode})" }
            val bytes = conn.inputStream.use { input ->
                val out = java.io.ByteArrayOutputStream()
                val buf = ByteArray(8192)
                while (true) {
                    val n = input.read(buf)
                    if (n < 0) break
                    check(out.size() + n <= 1000000) { "Response too large" }
                    out.write(buf, 0, n)
                }
                out.toByteArray()
            }
            return JSONObject(bytes.toString(Charsets.UTF_8))
        } finally { conn.disconnect() }
    }
}
