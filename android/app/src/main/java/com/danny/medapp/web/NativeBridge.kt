package com.danny.medapp.web

import android.webkit.JavascriptInterface
import com.danny.medapp.BuildConfig
import com.danny.medapp.net.ServerSettings

/**
 * 页面与原生层的桥。GET 由 WebViewClient 转发，带请求体的写操作通过这里执行，
 * 因为 Android 的 shouldInterceptRequest 不暴露原始请求体。
 */
class NativeBridge(
    private val serverSettings: ServerSettings,
    private val submitRequest: (
        id: String,
        method: String,
        path: String,
        body: String?,
        authorization: String?,
    ) -> Unit,
    private val showToast: (String) -> Unit,
    private val hapticFeedback: () -> Unit,
    private val onSystemBarsDarkChanged: (Boolean) -> Unit,
) {

    @JavascriptInterface
    fun getServerUrl(): String = serverSettings.baseUrl

    @JavascriptInterface
    fun setServerUrl(value: String): Boolean {
        if (!ServerSettings.isValid(value)) return false
        serverSettings.baseUrl = value
        return true
    }

    @JavascriptInterface
    fun request(
        id: String,
        method: String,
        path: String,
        body: String?,
        authorization: String?,
    ) {
        val normalizedMethod = method.uppercase()
        if (normalizedMethod !in setOf("POST", "PUT", "PATCH", "DELETE")) {
            submitRequest(id, "ERROR", path, "不支持的请求方法", authorization)
            return
        }
        if (!ApiRoutes.isAllowedApiPath(path)) {
            submitRequest(id, "ERROR", path, "接口路径不合法", authorization)
            return
        }
        submitRequest(id, normalizedMethod, path, body, authorization)
    }

    @JavascriptInterface
    fun toast(message: String) = showToast(message)

    @JavascriptInterface
    fun haptic() = hapticFeedback()

    @JavascriptInterface
    fun setSystemBarsDark(dark: Boolean) = onSystemBarsDarkChanged(dark)

    @JavascriptInterface
    fun appVersion(): String = BuildConfig.VERSION_NAME
}
