package com.danny.medapp.web

import org.junit.Assert.assertEquals
import org.junit.Test

class JsonTest {

    @Test
    fun escapesBridgePayloadCharacters() {
        assertEquals(
            "\"line\\nquote\\\"slash\\\\tab\\t\"",
            Json.quote("line\nquote\"slash\\tab\t"),
        )
    }

    @Test
    fun buildsFastApiCompatibleError() {
        assertEquals("{\"detail\":\"网络\\n不可用\"}", Json.detail("网络\n不可用"))
    }
}
