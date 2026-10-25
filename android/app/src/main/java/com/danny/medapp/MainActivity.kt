package com.danny.medapp

import android.annotation.SuppressLint
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.res.Configuration
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.webkit.ConsoleMessage
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.core.view.updatePadding
import androidx.webkit.WebSettingsCompat
import androidx.webkit.WebViewFeature
import androidx.webkit.WebViewAssetLoader
import com.danny.medapp.databinding.ActivityMainBinding
import com.danny.medapp.net.ServerSettings
import com.danny.medapp.net.UpstreamClient
import com.danny.medapp.web.ApiRoutes
import com.danny.medapp.web.AppWebViewClient
import com.danny.medapp.web.Json
import com.danny.medapp.web.NativeBridge
import java.io.IOException
import java.net.HttpURLConnection
import java.util.concurrent.Executors

/** 单 Activity：本地打包的移动工作台 + 原生 API 转发。 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var serverSettings: ServerSettings
    private lateinit var bridge: NativeBridge
    private val upstream = UpstreamClient()
    private val ioExecutor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        serverSettings = ServerSettings(this)

        setUpEdgeToEdge()
        setUpWebView()
        setUpBackNavigation()

        binding.swipeRefresh.setColorSchemeColors(getColor(R.color.brand_primary))
        binding.swipeRefresh.setOnRefreshListener { binding.webView.reload() }

        val restored = savedInstanceState?.let { binding.webView.restoreState(it) }
        if (restored == null) {
            binding.webView.loadUrl(ApiRoutes.ASSET_URL)
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setUpWebView() {
        val webView = binding.webView
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = false
            allowContentAccess = false
            setSupportZoom(false)
            builtInZoomControls = false
            displayZoomControls = false
            mediaPlaybackRequiresUserGesture = true
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
        }
        if (WebViewFeature.isFeatureSupported(WebViewFeature.ALGORITHMIC_DARKENING)) {
            WebSettingsCompat.setAlgorithmicDarkeningAllowed(webView.settings, false)
        }

        val assetLoader = WebViewAssetLoader.Builder()
            .setDomain(ApiRoutes.ASSET_HOST)
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()

        bridge = NativeBridge(
            serverSettings = serverSettings,
            submitRequest = ::submitRequest,
            showToast = ::showToast,
            hapticFeedback = {
                binding.webView.performHapticFeedback(
                    android.view.HapticFeedbackConstants.KEYBOARD_TAP,
                )
            },
        )
        webView.addJavascriptInterface(bridge, "MedSalesApp")

        webView.webViewClient = AppWebViewClient(
            assetLoader = assetLoader,
            upstream = upstream,
            serverSettings = serverSettings,
            onExternalLink = ::openExternally,
            onPageFinished = { binding.swipeRefresh.isRefreshing = false },
        )
        webView.webChromeClient = object : WebChromeClient() {
            override fun onConsoleMessage(message: ConsoleMessage): Boolean {
                if (BuildConfig.DEBUG) {
                    Log.d(TAG, "${message.message()} (${message.sourceId()}:${message.lineNumber()})")
                }
                return true
            }
        }
    }

    private fun submitRequest(
        id: String,
        method: String,
        path: String,
        body: String?,
        authorization: String?,
    ) {
        ioExecutor.execute {
            val response = try {
                if (method == "ERROR") {
                    Pair(HttpURLConnection.HTTP_BAD_REQUEST, Json.detail(body ?: "请求失败"))
                } else {
                    val result = upstream.execute(
                        baseUrl = serverSettings.baseUrl,
                        method = method,
                        path = path,
                        body = body,
                        authorization = authorization,
                    )
                    Pair(result.status, result.body)
                }
            } catch (e: IOException) {
                Pair(0, Json.detail("无法连接服务器，请检查服务器地址和网络"))
            } catch (e: IllegalArgumentException) {
                Pair(0, Json.detail("请求地址有误：${e.message.orEmpty()}"))
            } catch (e: Exception) {
                Pair(0, Json.detail("请求失败：${e.message.orEmpty()}"))
            }
            mainHandler.post {
                binding.webView.evaluateJavascript(
                    "window.appBridge&&window.appBridge.onApiResponse(" +
                        "${Json.quote(id)},${response.first},${Json.quote(response.second)})",
                    null,
                )
            }
        }
    }

    private fun showToast(message: String) {
        mainHandler.post {
            Toast.makeText(this, message.take(160), Toast.LENGTH_SHORT).show()
        }
    }

    private fun setUpEdgeToEdge() {
        WindowCompat.setDecorFitsSystemWindows(window, false)
        ViewCompat.setOnApplyWindowInsetsListener(binding.root) { view, insets ->
            val bars = insets.getInsets(
                WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout(),
            )
            val ime = insets.getInsets(WindowInsetsCompat.Type.ime())
            view.updatePadding(
                left = bars.left,
                top = bars.top,
                right = bars.right,
                bottom = maxOf(bars.bottom, ime.bottom),
            )
            insets
        }

        val night = resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK ==
            Configuration.UI_MODE_NIGHT_YES
        WindowInsetsControllerCompat(window, binding.root).apply {
            isAppearanceLightStatusBars = !night
            isAppearanceLightNavigationBars = !night
        }
    }

    private fun setUpBackNavigation() {
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                val webView = binding.webView
                // 单页界面使用 hash 路由，WebView 的原生历史不总是包含页面内跳转。
                // 先让页面决定是否消费返回事件，再决定回退或退出 Activity。
                webView.evaluateJavascript(
                    "window.medappBack ? window.medappBack() : 'exit'",
                ) { result ->
                    when {
                        result == "\"handled\"" -> Unit
                        result == "\"exit\"" -> {
                            isEnabled = false
                            onBackPressedDispatcher.onBackPressed()
                        }
                        webView.canGoBack() -> webView.goBack()
                        else -> {
                            isEnabled = false
                            onBackPressedDispatcher.onBackPressed()
                        }
                    }
                }
            }
        })
    }

    private fun openExternally(uri: Uri) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, uri))
        } catch (e: ActivityNotFoundException) {
            Toast.makeText(this, R.string.no_app_for_link, Toast.LENGTH_SHORT).show()
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        binding.webView.saveState(outState)
    }

    override fun onDestroy() {
        ioExecutor.shutdownNow()
        upstream.close()
        super.onDestroy()
    }

    private companion object {
        const val TAG = "medapp"
    }
}
