package id.manajemen.mikrotik

import android.app.Activity
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.TextView
import android.widget.LinearLayout
import android.graphics.Color
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import kotlin.concurrent.thread

class MainActivity : Activity() {

    private lateinit var webView: WebView
    private val handler = Handler(Looper.getMainLooper())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(11, 18, 32))
        }

        val status = TextView(this).apply {
            text = "MANAJEMEN MIKROTIK\nMenyiapkan koneksi..."
            textSize = 18f
            setTextColor(Color.WHITE)
            setPadding(24, 30, 24, 30)
        }

        webView = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            webViewClient = WebViewClient()
        }

        layout.addView(status)
        layout.addView(
            webView,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f
            )
        )

        setContentView(layout)

        thread {
            try {
                if (!Python.isStarted()) {
                    Python.start(AndroidPlatform(this))
                }

                val module = Python.getInstance().getModule("app")
                module.callAttr("start_server")

                handler.postDelayed({
                    status.text = "MANAJEMEN MIKROTIK"
                    webView.loadUrl("http://127.0.0.1:8765/")
                }, 1500)

            } catch (e: Exception) {
                handler.post {
                    status.text = "GAGAL MENJALANKAN SERVER:\n${e.message}"
                }
            }
        }
    }

    override fun onDestroy() {
        webView.destroy()
        super.onDestroy()
    }
}
