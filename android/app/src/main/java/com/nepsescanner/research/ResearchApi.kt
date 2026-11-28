package com.nepsescanner.research

import java.net.URI
import javax.net.ssl.HttpsURLConnection
import org.json.JSONObject

class ResearchApi(base: String) {
    private val origin = URI(base.trim()).also {
        require(it.scheme == "https" && it.host != null && it.userInfo == null &&
            it.query == null && it.fragment == null && (it.path.isNullOrEmpty() || it.path == "/"))
    }
    fun marketHealth(): JSONObject = get("/v1/market-health")
    fun readiness(): JSONObject = get("/v1/research/readiness")
    fun history(symbol: String): JSONObject = get("/v1/data/"+symbolKey(symbol))
    fun scan(symbol: String): JSONObject = get("/v1/scan", JSONObject().put("symbols",org.json.JSONArray().put(symbolKey(symbol))))
    fun brokers(symbol: String, start: String, end: String): JSONObject {
        require(java.time.LocalDate.parse(start).toString()==start && java.time.LocalDate.parse(end).toString()==end && start<=end)
        return get("/v1/broker/summary/"+symbolKey(symbol)+"?start="+start+"&end="+end)
    }
    private fun symbolKey(symbol: String): String = symbol.trim().uppercase(java.util.Locale.ROOT).also { require(it.matches(Regex("[A-Z0-9]{1,20}"))) }
    private fun get(path: String, body: JSONObject? = null): JSONObject {
        val conn = origin.resolve(path).toURL().openConnection() as HttpsURLConnection
        try {
            conn.instanceFollowRedirects = false
            conn.connectTimeout = 10000
            conn.readTimeout = 10000
            conn.setRequestProperty("Accept", "application/json")
            if (body != null) {
                conn.requestMethod = "POST"
                conn.doOutput = true
                conn.setRequestProperty("Content-Type", "application/json")
                conn.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
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
