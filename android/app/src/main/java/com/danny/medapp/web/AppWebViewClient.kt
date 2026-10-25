package com.danny.medapp.web

import android.net.Uri
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.webkit.WebViewAssetLoader
import com.danny.medapp.net.ServerSettings
import com.danny.medapp.net.UpstreamClient
import okhttp3.Response
import java.io.ByteArrayInputStream
import java.io.IOException
import java.net.HttpURLConnection

/** 本地静态资源由 AssetLoader 提供，GET API 请求由原生客户端代理。 */
class AppWebViewClient(
    private val assetLoader: WebViewAssetLoader,
    private val upstream: UpstreamClient,
    private val serverSettings: ServerSettings,
    private val onExternalLink: (Uri) -> Unit,
    private val onPageFinished: () -> Unit,
) : WebViewClient() {

    override fun shouldInterceptRequest(
        view: WebView,
        request: WebResourceRequest,
    ): WebResourceResponse? {
        val url = request.url
        if (url.host == ApiRoutes.ASSET_HOST && ApiRoutes.isApiPath(url.path.orEmpty())) {
            if (request.method != "GET") {
                return errorResponse(
                    HttpURLConnection.HTTP_BAD_METHOD,
                    "写操作请通过原生桥提交",
                )
            }
            val authorization = request.requestHeaders.entries
                .firstOrNull { it.key.equals("Authorization", ignoreCase = true) }
                ?.value
            return proxy(url, authorization)
        }
        return assetLoader.shouldInterceptRequest(url)
    }

    override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
        val url = request.url
        if (url.host == ApiRoutes.ASSET_HOST) return false
        onExternalLink(url)
        return true
    }

    override fun onPageFinished(view: WebView, url: String) {
        onPageFinished()
    }

    override fun onReceivedError(
        view: WebView,
        request: WebResourceRequest,
        error: WebResourceError,
    ) {
        if (!request.isForMainFrame) return
        onPageFinished()
        view.loadDataWithBaseURL(ApiRoutes.ASSET_URL, ERROR_PAGE, "text/html", "utf-8", null)
    }

    private fun proxy(url: Uri, authorization: String?): WebResourceResponse {
        return try {
            val response = upstream.get(
                baseUrl = serverSettings.baseUrl,
                path = url.path.orEmpty(),
                query = url.query,
                authorization = authorization,
            )
            val body = response.body
            if (body == null) {
                response.close()
                errorResponse(HttpURLConnection.HTTP_BAD_GATEWAY, "服务端返回了空响应")
            } else {
                WebResourceResponse(
                    mimeType(response),
                    charset(response),
                    response.code,
                    response.message.ifEmpty { "OK" },
                    passthroughHeaders(response),
                    body.byteStream(),
                )
            }
        } catch (e: IOException) {
            errorResponse(
                HttpURLConnection.HTTP_BAD_GATEWAY,
                "无法连接 medapp 服务，请检查服务器地址和网络",
            )
        } catch (e: IllegalArgumentException) {
            errorResponse(
                HttpURLConnection.HTTP_INTERNAL_ERROR,
                "后端地址配置有误",
            )
        }
    }

    private fun mimeType(response: Response): String =
        response.header("Content-Type")
            ?.substringBefore(';')
            ?.trim()
            ?.takeIf { it.isNotEmpty() }
            ?: "application/json"

    private fun charset(response: Response): String? {
        val mime = mimeType(response)
        return if (mime.startsWith("text/") || mime.contains("json") || mime.contains("xml")) {
            "utf-8"
        } else {
            null
        }
    }

    private fun passthroughHeaders(response: Response): Map<String, String> =
        PASSTHROUGH_HEADERS.mapNotNull { name -> response.header(name)?.let { name to it } }.toMap()

    private fun errorResponse(status: Int, message: String): WebResourceResponse =
        WebResourceResponse(
            "application/json",
            "utf-8",
            status,
            "Upstream Error",
            mapOf("Cache-Control" to "no-store"),
            ByteArrayInputStream(Json.detail(message).toByteArray(Charsets.UTF_8)),
        )

    private companion object {
        val PASSTHROUGH_HEADERS = listOf("Cache-Control", "ETag", "Last-Modified", "Expires")

        val ERROR_PAGE = """
            <!doctype html>
            <html lang="zh-CN">
            <head>
              <meta charset="utf-8" />
              <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
              <title>medapp</title>
              <style>
                :root { color-scheme: light dark; }
                body { margin: 0; min-height: 100vh; display: grid; place-items: center;
                       font-family: system-ui, -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
                       background: #f4f7f9; color: #102a43; }
                main { text-align: center; padding: 32px; max-width: 340px; }
                .mark { width: 64px; height: 64px; border-radius: 20px; margin: 0 auto 20px;
                        display: grid; place-items: center; background: #0e7490; color: #fff;
                        font-size: 34px; font-weight: 800; }
                h1 { font-size: 20px; margin: 0 0 8px; }
                p { margin: 0 0 22px; color: #4b6576; font-size: 15px; line-height: 1.6; }
                a { display: inline-flex; min-height: 48px; align-items: center; padding: 0 24px;
                    border-radius: 14px; color: #fff; text-decoration: none; font-weight: 700;
                    background: #0e7490; }
                @media (prefers-color-scheme: dark) {
                  body { background: #071a20; color: #eaf6f8; }
                  p { color: #a7bec6; }
                  .mark, a { background: #67e8f9; color: #062b33; }
                }
              </style>
            </head>
            <body>
              <main>
                <div class="mark" aria-hidden="true">+</div>
                <h1>页面加载失败</h1>
                <p>应用界面没有正常加载，请重试。</p>
                <a href="index.html">重新加载</a>
              </main>
            </body>
            </html>
        """.trimIndent()
    }
}
