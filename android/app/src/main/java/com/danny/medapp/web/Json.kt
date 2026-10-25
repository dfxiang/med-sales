package com.danny.medapp.web

/** 原生回调页面时使用的最小 JSON 编码器。 */
object Json {

    fun quote(value: String): String = buildString {
        append('"')
        for (ch in value) {
            when (ch) {
                '"' -> append("\\\"")
                '\\' -> append("\\\\")
                '\n' -> append("\\n")
                '\r' -> append("\\r")
                '\t' -> append("\\t")
                '\b' -> append("\\b")
                '\u000C' -> append("\\f")
                '\u2028' -> append("\\u2028")
                '\u2029' -> append("\\u2029")
                else -> {
                    if (ch < ' ') append("\\u%04x".format(ch.code)) else append(ch)
                }
            }
        }
        append('"')
    }

    fun detail(message: String): String = "{\"detail\":${quote(message)}}"
}
