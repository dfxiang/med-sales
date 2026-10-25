package com.danny.medapp.web

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ApiRoutesTest {

    @Test
    fun detectsOnlyApiPaths() {
        assertTrue(ApiRoutes.isApiPath("/api"))
        assertTrue(ApiRoutes.isApiPath("/api/sales-orders"))
        assertFalse(ApiRoutes.isApiPath("/assets/www/index.html"))
        assertFalse(ApiRoutes.isApiPath("/apix/sales-orders"))
    }

    @Test
    fun rejectsUnsafeMutationPaths() {
        assertTrue(ApiRoutes.isAllowedApiPath("/api/auth/login"))
        assertFalse(ApiRoutes.isAllowedApiPath("/api/../admin"))
        assertFalse(ApiRoutes.isAllowedApiPath("/other"))
        assertFalse(ApiRoutes.isAllowedApiPath("/api/auth/login\nInjected: true"))
    }

    @Test
    fun joinsBasePathAndQueryWithoutReencoding() {
        assertEquals(
            "http://127.0.0.1:8001/api/inventory?page=1&size=20",
            ApiRoutes.upstreamUrl(
                "http://127.0.0.1:8001/",
                "/api/inventory",
                "page=1&size=20",
            ),
        )
    }
}
