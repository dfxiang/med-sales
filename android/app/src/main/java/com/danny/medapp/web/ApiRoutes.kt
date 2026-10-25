package com.danny.medapp.web

/** 本地素材域与上游 API 的路径约定。 */
object ApiRoutes {

    const val ASSET_HOST = "appassets.androidplatform.net"
    const val ASSET_URL = "https://$ASSET_HOST/assets/www/index.html"

    private const val API_PREFIX = "/api/"

    fun isApiPath(path: String): Boolean = path == "/api" || path.startsWith(API_PREFIX)

    fun isAllowedApiPath(path: String): Boolean =
        path.startsWith(API_PREFIX) && !path.contains("..") && !path.contains("\n")

    fun upstreamUrl(baseUrl: String, path: String, query: String?): String {
        val base = baseUrl.trimEnd('/')
        return if (query.isNullOrEmpty()) base + path else "$base$path?$query"
    }
}
