package com.danny.medapp.web

import com.danny.medapp.net.UpstreamClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test

class UpstreamClientTest {

    private lateinit var server: MockWebServer
    private lateinit var client: UpstreamClient

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
        client = UpstreamClient()
    }

    @After
    fun tearDown() {
        client.close()
        server.shutdown()
    }

    @Test
    fun forwardsAuthenticatedJsonPost() {
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"access_token":"token-value"}"""),
        )

        val result = client.execute(
            baseUrl = server.url("/").toString().trimEnd('/'),
            method = "POST",
            path = "/api/auth/login",
            body = """{"username":"admin","password":"secret"}""",
            authorization = "Bearer token-value",
        )

        assertEquals(200, result.status)
        assertEquals("""{"access_token":"token-value"}""", result.body)
        val request = server.takeRequest()
        assertEquals("POST", request.method)
        assertEquals("/api/auth/login", request.path)
        assertEquals("Bearer token-value", request.getHeader("Authorization"))
        assertEquals(
            """{"username":"admin","password":"secret"}""",
            request.body.readUtf8(),
        )
    }

    @Test
    fun forwardsGetQueryAndAuthorizationHeader() {
        server.enqueue(MockResponse().setBody("""{"items":[],"total":0}"""))

        val response = client.get(
            baseUrl = server.url("/").toString().trimEnd('/'),
            path = "/api/sales-orders",
            query = "page=1&size=20&status=%E5%BE%85%E4%BB%98%E6%AC%BE",
            authorization = "Bearer read-token",
        )
        response.use {
            assertEquals(200, it.code)
            assertEquals("""{"items":[],"total":0}""", it.body?.string())
        }

        val request = server.takeRequest()
        assertEquals("GET", request.method)
        assertEquals(
            "/api/sales-orders?page=1&size=20&status=%E5%BE%85%E4%BB%98%E6%AC%BE",
            request.path,
        )
        assertEquals("Bearer read-token", request.getHeader("Authorization"))
    }
}
