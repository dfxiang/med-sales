package com.danny.medapp.net

import com.danny.medapp.BuildConfig
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import java.util.concurrent.TimeUnit

data class ApiResult(val status: Int, val body: String)

/** 原生请求层：WebView 只访问本地素材，API 请求统一从这里发往后端。 */
class UpstreamClient {

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .callTimeout(45, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .build()

    fun get(
        baseUrl: String,
        path: String,
        query: String?,
        authorization: String?,
        contentType: String? = null,
    ): Response {
        val request = newRequest(
            baseUrl = baseUrl,
            method = "GET",
            path = path,
            query = query,
            body = null,
            authorization = authorization,
            contentType = contentType,
        )
        return client.newCall(request).execute()
    }

    fun execute(
        baseUrl: String,
        method: String,
        path: String,
        body: String?,
        authorization: String?,
    ): ApiResult {
        val request = newRequest(
            baseUrl = baseUrl,
            method = method,
            path = path,
            query = null,
            body = body,
            authorization = authorization,
            contentType = "application/json; charset=utf-8",
        )
        return client.newCall(request).execute().use { response ->
            ApiResult(response.code, response.body?.string().orEmpty())
        }
    }

    private fun newRequest(
        baseUrl: String,
        method: String,
        path: String,
        query: String?,
        body: String?,
        authorization: String?,
        contentType: String?,
    ): Request {
        val base = baseUrl.trimEnd('/')
        val url = if (query.isNullOrEmpty()) "$base$path" else "$base$path?$query"
        val builder = Request.Builder()
            .url(url)
            .header("Accept", "application/json")
            .header("User-Agent", "medapp-android/${BuildConfig.VERSION_NAME}")

        if (!authorization.isNullOrBlank()) {
            builder.header("Authorization", authorization)
        }

        when (method.uppercase()) {
            "GET" -> builder.get()
            "POST", "PUT", "PATCH", "DELETE" -> {
                val mediaType = (contentType ?: "application/json; charset=utf-8").toMediaType()
                val requestBody = (body ?: "").toRequestBody(mediaType)
                builder.method(method.uppercase(), requestBody)
            }
            else -> error("不支持的请求方法：$method")
        }
        return builder.build()
    }

    fun close() {
        client.dispatcher.executorService.shutdown()
        client.connectionPool.evictAll()
    }
}
