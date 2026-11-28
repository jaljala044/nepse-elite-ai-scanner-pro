package com.nepsescanner.research

import org.junit.Test
import org.junit.Assert.*
import java.net.URI

class MobileSessionTest {
    @Test fun expirationAndClear() {
        var now=1000L
        val token="a".repeat(43)
        val session=MobileSession("https://example.com",token,10){now}
        assertEquals("Bearer "+token,session.authorizationFor(URI("https://example.com")))
        now=11000L
        assertThrows(IllegalStateException::class.java) { session.authorizationFor(URI("https://example.com")) }
        val other=MobileSession("https://example.com",token,10){now}
        other.clear()
        assertThrows(IllegalStateException::class.java) { other.authorizationFor(URI("https://example.com")) }
    }
    @Test fun originIsolation() {
        val s=MobileSession("https://example.com","a".repeat(43),900){0L}
        assertEquals("Bearer "+"a".repeat(43),s.authorizationFor(URI("https://example.com:443")))
        for(target in listOf("http://example.com","https://other.example.com","https://example.com:444")) {
            assertThrows(IllegalArgumentException::class.java) { s.authorizationFor(URI(target)) }
        }
        assertThrows(IllegalArgumentException::class.java) { MobileSession("http://example.com","a".repeat(43),900){0L} }
        assertThrows(IllegalArgumentException::class.java) { MobileSession("https://example.com","bad",900){0L} }
    }
}
