package com.nepsescanner.research

import java.net.URI

/** Memory-only session. A trusted gateway must supply an exchanged token.
 * Never persist or transmit it to an unrelated origin. */
class MobileSession(base: String, token: String, expiresIn: Int, private val clock: () -> Long = { android.os.SystemClock.elapsedRealtime() }) {
    private val origin = URI(base.trim()).also {
        require(it.scheme=="https" && it.host!=null && it.userInfo==null && it.query==null && it.fragment==null && (it.path.isNullOrEmpty() || it.path=="/"))
    }
    private var accessToken: String? = token.also { require(it.matches(Regex("[A-Za-z0-9_-]{43}"))) }
    private val deadline = clock() + expiresIn.also { require(it in 1..900) }*1000L
    @Synchronized fun authorizationFor(target: URI): String {
        require(target.scheme==origin.scheme && target.host.equals(origin.host,true) && port(target)==port(origin))
        if(clock()>=deadline) clear()
        return "Bearer "+checkNotNull(accessToken) { "Session expired or cleared" }
    }
    @Synchronized fun clear() { accessToken=null }
    private fun port(uri: URI)=if(uri.port==-1) 443 else uri.port
}
