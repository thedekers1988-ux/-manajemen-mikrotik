
package id.manajemen.mikrotik

import android.app.Activity
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.LinearLayout
import android.widget.TextView
import android.graphics.Color
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import kotlin.concurrent.thread

class MainActivity : Activity() {

    private lateinit var webView: WebView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(11, 18, 32))
        }

        val status = TextView(this).apply {
            text = "MANAJEMEN MIKROTIK\nMenyiapkan aplikasi..."
            textSize = 18f
            setTextColor(Color.WHITE)
            setPadding(20, 24, 20, 24)
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

                module.callAttr(
                    "start_server",
                    filesDir.absolutePath
                )

                Handler(Looper.getMainLooper()).postDelayed({
                    status.text = "MANAJEMEN MIKROTIK"
                    webView.loadUrl("http://127.0.0.1:8765/")
                }, 1500)

            } catch (e: Exception) {
                Handler(Looper.getMainLooper()).post {
                    status.text =
                        "GAGAL MEMBUKA APLIKASI:\n${e.message}"
                }
            }
        }
    }

    override fun onDestroy() {
        webView.destroy()
        super.onDestroy()
    }
}
