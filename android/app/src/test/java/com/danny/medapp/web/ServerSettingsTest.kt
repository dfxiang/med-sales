package com.danny.medapp.web

import com.danny.medapp.net.ServerSettings
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ServerSettingsTest {

    @Test
    fun acceptsHttpAndHttpsRootAddresses() {
        assertTrue(ServerSettings.isValid("http://10.0.2.2:8001"))
        assertTrue(ServerSettings.isValid("https://med-sales.example.com"))
        assertTrue(ServerSettings.isValid("http://192.168.1.20:8001/"))
    }

    @Test
    fun rejectsPathsQueriesAndUnsupportedSchemes() {
        assertFalse(ServerSettings.isValid("10.0.2.2:8001"))
        assertFalse(ServerSettings.isValid("ftp://10.0.2.2:8001"))
        assertFalse(ServerSettings.isValid("http://10.0.2.2:8001/api"))
        assertFalse(ServerSettings.isValid("http://10.0.2.2:8001?token=x"))
    }

    @Test
    fun normalizesTrailingWhitespaceAndSlash() {
        assertEquals("http://127.0.0.1:8001", ServerSettings.normalize("  http://127.0.0.1:8001/ "))
    }
}
