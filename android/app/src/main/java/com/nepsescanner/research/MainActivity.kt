package com.nepsescanner.research

import android.app.Activity
import android.os.Bundle
import android.widget.*
import android.graphics.Color
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private val worker = Executors.newSingleThreadExecutor()
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 48, 24, 24)
            setBackgroundColor(Color.rgb(11,17,27))
        }
        val title = TextView(this).apply { text = "NEPSE Scanner"; textSize = 26f; setTextColor(Color.WHITE) }
        val note = TextView(this).apply { text = "Research only • AI recommendations disabled"; setTextColor(Color.LTGRAY) }
        val endpoint = EditText(this).apply { hint = "HTTPS research API origin"; inputType = 17; setSingleLine(true) }
        val button = Button(this).apply { text = "Check market evidence" }
        val status = TextView(this).apply { text = "No verified live feed connected."; setTextColor(Color.WHITE); textSize = 16f }
        listOf(title,note,endpoint,button,status).forEach { root.addView(it) }
        setContentView(ScrollView(this).apply { addView(root) })
        button.setOnClickListener {
            val base = endpoint.text.toString()
            button.isEnabled = false
            status.text = "Checking research API…"
            worker.execute {
                val result = runCatching {
                    val api = ResearchApi(base)
                    val health = api.marketHealth()
                    val ready = api.readiness()
                    check(ready.optString("mode") == "research_only")
                    "Market evidence: ${health.optString("status", "unknown")}\nDecision session: ${health.optString("decision_session", "unknown")}\nLive feed: not verified\nAI recommendations: OFF"
                }.getOrElse { "Research API unavailable. Check HTTPS endpoint and authorized access." }
                runOnUiThread { if (!isDestroyed) { status.text = result; button.isEnabled = true } }
            }
        }
    }
    override fun onDestroy() { worker.shutdownNow(); super.onDestroy() }
}
