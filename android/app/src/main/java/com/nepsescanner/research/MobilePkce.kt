package com.nepsescanner.research

import java.net.URI
import java.net.URLDecoder
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import java.security.SecureRandom
import java.util.Base64

/** Protocol primitives only. No identity provider or production login is activated. */
internal class MobilePkce(
    private val authorizationEndpoint: URI,
    private val clientId: String,
    private val redirectUri: URI,
    private val clock: () -> Long = { android.os.SystemClock.elapsedRealtime() },
    private val random: SecureRandom = SecureRandom()
) {
    internal data class Exchange(val code: String, val verifier: String, val redirectUri: String)
    private val verifier = randomToken()
    private val state = randomToken()
    private val deadline = clock() + 300_000L
    private var consumed = false

    init {
        require(authorizationEndpoint.scheme == "https" && authorizationEndpoint.host != null &&
            authorizationEndpoint.userInfo == null && authorizationEndpoint.fragment == null &&
            authorizationEndpoint.rawQuery == null)
        require(redirectUri.scheme == "https" && redirectUri.host != null &&
            redirectUri.userInfo == null && redirectUri.rawQuery == null &&
            redirectUri.fragment == null && !redirectUri.path.isNullOrBlank() && redirectUri.path != "/")
        require(clientId.isNotBlank() && clientId.length <= 256)
    }

    private fun randomToken(): String = Base64.getUrlEncoder().withoutPadding()
        .encodeToString(ByteArray(32).also { random.nextBytes(it) })
    private fun encode(value: String): String = URLEncoder.encode(value, "UTF-8")

    @Synchronized fun authorizationUri(): URI {
        check(!consumed && clock() < deadline)
        val challenge = Base64.getUrlEncoder().withoutPadding().encodeToString(
            MessageDigest.getInstance("SHA-256").digest(verifier.toByteArray(StandardCharsets.US_ASCII)))
        val params = linkedMapOf("response_type" to "code", "client_id" to clientId,
            "redirect_uri" to redirectUri.toASCIIString(), "state" to state,
            "code_challenge" to challenge, "code_challenge_method" to "S256")
        return URI.create(authorizationEndpoint.toASCIIString()+"?"+params.entries.joinToString("&") {
            encode(it.key)+"="+encode(it.value)
        })
    }

    @Synchronized fun consume(callback: URI): Exchange {
        check(!consumed && clock() < deadline) { "Authorization expired or consumed" }
        require(callback.scheme == redirectUri.scheme &&
            callback.host.equals(redirectUri.host, true) &&
            effectivePort(callback) == effectivePort(redirectUri) &&
            callback.rawPath == redirectUri.rawPath && callback.userInfo == null &&
            callback.fragment == null)
        val raw = requireNotNull(callback.rawQuery)
        require(raw.length <= 8192)
        val params = mutableMapOf<String,String>()
        raw.split("&").forEach { entry ->
            val parts = entry.split("=",limit=2)
            require(parts.size == 2)
            val key = URLDecoder.decode(parts[0],"UTF-8")
            val value = URLDecoder.decode(parts[1],"UTF-8")
            require(key in setOf("code","state","error","error_description","iss") && !params.containsKey(key))
            params[key] = value
        }
        val returnedState = requireNotNull(params["state"])
        require(MessageDigest.isEqual(state.toByteArray(StandardCharsets.UTF_8),
            returnedState.toByteArray(StandardCharsets.UTF_8))) { "Authorization state mismatch" }
        consumed = true
        require(!params.containsKey("error")) { "Authorization denied" }
        val code = requireNotNull(params["code"])
        require(code.isNotBlank() && code.length <= 4096 && code.none { it.isISOControl() })
        return Exchange(code,verifier,redirectUri.toASCIIString())
    }

    @Synchronized fun cancel() { consumed = true }
    private fun effectivePort(uri: URI): Int = if(uri.port == -1) 443 else uri.port
}
