
package id.manajemen.mikrotik

import android.app.Activity
import android.app.AlertDialog
import android.os.Bundle
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.widget.*
import org.json.JSONArray
import org.json.JSONObject

class MainActivity : Activity() {

    private val prefs by lazy {
        getSharedPreferences("mikrotik_data", MODE_PRIVATE)
    }

    private val blue = Color.rgb(35, 115, 230)
    private val dark = Color.rgb(15, 23, 42)
    private val white = Color.WHITE

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        render()
    }

    private fun dp(value: Int): Int =
        (value * resources.displayMetrics.density).toInt()

    private fun cardBackground(color: Int): GradientDrawable {
        return GradientDrawable().apply {
            setColor(color)
            cornerRadius = dp(16).toFloat()
        }
    }

    private fun text(
        value: String,
        size: Float,
        color: Int,
        bold: Boolean = false
    ): TextView {
        return TextView(this).apply {
            text = value
            textSize = size
            setTextColor(color)
            if (bold) setTypeface(null, Typeface.BOLD)
            setPadding(dp(12), dp(8), dp(12), dp(8))
        }
    }

    private fun render() {
        val scroll = ScrollView(this)
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(24), dp(18), dp(24))
            setBackgroundColor(dark)
        }

        scroll.addView(layout)
        setContentView(scroll)

        layout.addView(text(
            "MANAJEMEN MikroTik",
            25f, white, true
        ))

        layout.addView(text(
            "Monitoring dan Manajemen Jaringan",
            14f, Color.LTGRAY
        ))

        val status = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = cardBackground(
                Color.rgb(30, 41, 59)
            )
            setPadding(dp(12), dp(12), dp(12), dp(12))
        }

        status.addView(text(
            "DASHBOARD",
            17f, white, true
        ))

        status.addView(text(
            "Aplikasi berjalan langsung di HP Android",
            14f, Color.GREEN
        ))

        status.addView(text(
            "Server Kali Linux: Tidak diperlukan",
            13f, Color.LTGRAY
        ))

        layout.addView(status, marginParams())

        val addButton = Button(this).apply {
            text = "+ TAMBAH MIKROTIK"
            setTextColor(white)
            background = cardBackground(blue)
            setOnClickListener { addRouter() }
        }

        layout.addView(addButton, marginParams())

        layout.addView(text(
            "DAFTAR ROUTER",
            19f, white, true
        ))

        val routers = loadRouters()

        if (routers.length() == 0) {
            layout.addView(text(
                "Belum ada MikroTik ditambahkan.\nTekan tombol Tambah MikroTik.",
                14f, Color.LTGRAY
            ))
        }

        for (i in 0 until routers.length()) {
            val router = routers.getJSONObject(i)

            val item = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                background = cardBackground(
                    Color.rgb(30, 41, 59)
                )
                setPadding(dp(10), dp(10), dp(10), dp(10))
            }

            item.addView(text(
                router.optString("name"),
                17f, white, true
            ))

            item.addView(text(
                "IP: ${router.optString("ip")}",
                14f, Color.LTGRAY
            ))

            item.addView(text(
                "API Port: ${router.optString("port")}",
                13f, Color.LTGRAY
            ))

            val delete = Button(this).apply {
                text = "Hapus Router"
                setOnClickListener {
                    AlertDialog.Builder(this@MainActivity)
                        .setMessage("Hapus router ini?")
                        .setPositiveButton("Hapus") { _, _ ->
                            routers.remove(i)
                            saveRouters(routers)
                            render()
                        }
                        .setNegativeButton("Batal", null)
                        .show()
                }
            }

            item.addView(delete)
            layout.addView(item, marginParams())
        }

        layout.addView(text(
            "PELANGGAN PPPoE",
            19f, white, true
        ))

        layout.addView(text(
            "Data pelanggan akan ditampilkan setelah koneksi RouterOS API diaktifkan.",
            14f, Color.LTGRAY
        ))
    }

    private fun marginParams(): LinearLayout.LayoutParams {
        return LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply {
            bottomMargin = dp(14)
        }
    }

    private fun loadRouters(): JSONArray {
        return try {
            JSONArray(prefs.getString("routers", "[]"))
        } catch (e: Exception) {
            JSONArray()
        }
    }

    private fun saveRouters(data: JSONArray) {
        prefs.edit()
            .putString("routers", data.toString())
            .apply()
    }

    private fun addRouter() {
        val form = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(10), dp(20), dp(10))
        }

        val name = EditText(this).apply {
            hint = "Nama MikroTik"
        }

        val ip = EditText(this).apply {
            hint = "IP MikroTik"
            inputType = 0x00001002
        }

        val port = EditText(this).apply {
            hint = "Port API (8728)"
            setText("8728")
            inputType = 2
        }

        form.addView(name)
        form.addView(ip)
        form.addView(port)

        AlertDialog.Builder(this)
            .setTitle("Tambah MikroTik")
            .setView(form)
            .setPositiveButton("Simpan") { _, _ ->

                val n = name.text.toString().trim()
                val address = ip.text.toString().trim()
                val p = port.text.toString().trim()

                if (n.isEmpty() ||
                    address.isEmpty() ||
                    p.isEmpty()
                ) {
                    Toast.makeText(
                        this,
                        "Lengkapi semua data",
                        Toast.LENGTH_LONG
                    ).show()
                    return@setPositiveButton
                }

                val routers = loadRouters()

                val router = JSONObject().apply {
                    put("name", n)
                    put("ip", address)
                    put("port", p)
                }

                routers.put(router)
                saveRouters(routers)
                render()

                Toast.makeText(
                    this,
                    "Router berhasil disimpan",
                    Toast.LENGTH_SHORT
                ).show()
            }
            .setNegativeButton("Batal", null)
            .show()
    }
}
