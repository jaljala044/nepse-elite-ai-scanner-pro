package com.nepsescanner.research

import java.net.URI
import java.net.URLDecoder
import java.security.MessageDigest
import java.util.Base64
import org.junit.Test
import org.junit.Assert.*

class MobilePkceTest {
    private val redirect=URI("https://app.example.test/oauth/callback")
    private var now=1000L
    private fun flow()=MobilePkce(URI("https://identity.example.test/authorize"),"test-client",redirect,{now})
    private fun params(uri:URI)=uri.rawQuery.split("&").associate {
        val p=it.split("=",limit=2)
        URLDecoder.decode(p[0],"UTF-8") to URLDecoder.decode(p[1],"UTF-8")
    }
    private fun rejects(block:()->Unit) {
        assertTrue(runCatching(block).isFailure)
    }
    @Test fun challengeMatchesVerifierAndCallbackIsSingleUse(){
        val f=flow()
        val p=params(f.authorizationUri())
        assertEquals("S256",p["code_challenge_method"])
        assertEquals("code",p["response_type"])
        assertEquals(redirect.toString(),p["redirect_uri"])
        val cb=URI(redirect.toString()+"?state="+p["state"]+"&code=synthetic-code")
        val result=f.consume(cb)
        assertEquals("synthetic-code",result.code)
        assertEquals(43,result.verifier.length)
        assertEquals(p["code_challenge"],Base64.getUrlEncoder().withoutPadding().encodeToString(
            MessageDigest.getInstance("SHA-256").digest(result.verifier.toByteArray(Charsets.US_ASCII))))
        rejects { f.consume(cb) }
    }
    @Test fun wrongStateAndCallbackOriginAreRejected(){
        val f=flow()
        val state=params(f.authorizationUri())["state"]
        rejects { f.consume(URI(redirect.toString()+"?state=incorrect&code=test")) }
        rejects { f.consume(URI("https://other.example.test/oauth/callback?state=$state&code=test")) }
        rejects { f.consume(URI("https://app.example.test:8443/oauth/callback?state=$state&code=test")) }
        rejects { f.consume(URI("https://app.example.test/wrong?state=$state&code=test")) }
        rejects { f.consume(URI(redirect.toString()+"?state=$state&state=$state&code=test")) }
    }
    @Test fun expiresAndCancellationAreEnforced(){
        val f=flow()
        val state=params(f.authorizationUri())["state"]
        now+=300000L
        rejects { f.consume(URI(redirect.toString()+"?state=$state&code=test")) }
        val next=flow()
        val s=params(next.authorizationUri())["state"]
        next.cancel()
        rejects { next.consume(URI(redirect.toString()+"?state=$s&code=test")) }
    }
    @Test fun authorizationErrorConsumesTransaction(){
        val f=flow()
        val state=params(f.authorizationUri())["state"]
        rejects { f.consume(URI(redirect.toString()+"?state=$state&error=access_denied")) }
        rejects { f.consume(URI(redirect.toString()+"?state=$state&code=test")) }
    }
}
