package com.danny.medapp.net

import android.content.Context
import com.danny.medapp.BuildConfig
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull

/** 后端地址保存在本机，支持模拟器和同一局域网内的真机切换。 */
class ServerSettings(context: Context) {

    private val preferences =
        context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)

    var baseUrl: String
        get() = preferences.getString(KEY_BASE_URL, BuildConfig.API_BASE_URL)
            ?.let(::normalize)
            ?: BuildConfig.API_BASE_URL
        set(value) {
            preferences.edit().putString(KEY_BASE_URL, normalize(value)).apply()
        }

    companion object {
        private const val PREFERENCES_NAME = "medapp_server"
        private const val KEY_BASE_URL = "base_url"

        /**
         * 只接受带协议和主机的 HTTP(S) 根地址。拒绝用户名、查询参数和子路径，
         * 防止拼接 /api 时产生歧义。
         */
        fun isValid(value: String): Boolean {
            val normalized = normalize(value)
            val url = normalized.toHttpUrlOrNull() ?: return false
            return (url.scheme == "http" || url.scheme == "https") &&
                url.encodedPath == "/" &&
                url.query == null &&
                url.fragment == null &&
                url.username.isEmpty() &&
                url.password.isEmpty()
        }

        fun normalize(value: String): String = value.trim().trimEnd('/')
    }
}
