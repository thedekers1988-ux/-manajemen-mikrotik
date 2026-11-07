
package id.manajemen.mikrotik

import android.app.Activity
import android.app.AlertDialog
import android.os.Bundle
import android.graphics.Color
import android.graphics.Typeface
import android.text.InputType
import android.text.InputFilter
import android.view.ViewGroup
import android.widget.*
import org.json.JSONArray
import org.json.JSONObject

class MainActivity : Activity() {

    private val bg = Color.rgb(15, 23, 42)
    private val card = Color.rgb(30, 41, 59)
    private val blue = Color.rgb(37, 99, 235)
    private val white = Color.WHITE
    private val gray = Color.LTGRAY

    private val prefs by lazy {
        getSharedPreferences("mikrotik_data", MODE_PRIVATE)
    }

    private lateinit var root: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        render()
    }

    private fun dp(value: Int): Int {
        return (value * resources.displayMetrics.density).toInt()
    }

    private fun makeText(
        value: String,
        size: Float,
        color: Int = white,
        bold: Boolean = false
    ): TextView {
        return TextView(this).apply {
            text = value
            textSize = size
            setTextColor(color)
            if (bold) setTypeface(null, Typeface.BOLD)
            setPadding(dp(5), dp(8), dp(5), dp(8))
        }
    }

    private fun marginParams(): LinearLayout.LayoutParams {
        return LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT
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

    private fun render() {

        root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(20), dp(20), dp(20))
            setBackgroundColor(bg)
        }

        val scroll = ScrollView(this)
        scroll.addView(root)
        setContentView(scroll)

        root.addView(
            makeText("MANAJEMEN MikroTik", 27f, white, true),
            marginParams()
        )

        root.addView(
            makeText("Monitoring dan Manajemen Jaringan", 16f, gray),
            marginParams()
        )

        val dashboard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(20), dp(20), dp(20))
            setBackgroundColor(card)
        }

        dashboard.addView(
            makeText("DASHBOARD", 21f, white, true)
        )

        dashboard.addView(
            makeText(
                "Aplikasi berjalan langsung di HP Android",
                16f,
                Color.GREEN
            )
        )

        dashboard.addView(
            makeText("Server Kali Linux: Tidak diperlukan", 14f, gray)
        )

        root.addView(dashboard, marginParams())

        val addButton = Button(this).apply {
            text = "+ TAMBAH MIKROTIK"
            setTextColor(white)
            setBackgroundColor(blue)
            setOnClickListener {
                addRouter()
            }
        }

        root.addView(addButton, marginParams())

        root.addView(
            makeText("DAFTAR ROUTER", 21f, white, true),
            marginParams()
        )

        val routers = loadRouters()

        if (routers.length() == 0) {
            root.addView(
                makeText(
                    "Belum ada MikroTik ditambahkan.\nTekan tombol Tambah MikroTik.",
                    15f,
                    gray
                )
            )
        }

        for (i in 0 until routers.length()) {

            val router = routers.getJSONObject(i)

            val name = router.optString("name")
            val ip = router.optString("ip")
            val port = router.optString("port")

            val item = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(16), dp(12), dp(16), dp(12))
                setBackgroundColor(card)
            }

            item.addView(
                makeText(name, 19f, white, true)
            )

            item.addView(
                makeText("IP: $ip:$port", 15f, gray)
            )

            item.addView(
                makeText(
                    "Username: ${router.optString("username")}",
                    14f,
                    gray
                )
            )

            val deleteButton = Button(this).apply {
                text = "HAPUS ROUTER"
                setOnClickListener {
                    AlertDialog.Builder(this@MainActivity)
                        .setTitle("Hapus Router")
                        .setMessage("Hapus $name?")
                        .setPositiveButton("Hapus") { _, _ ->

                            val updated = JSONArray()

                            for (j in 0 until routers.length()) {
                                if (j != i) {
                                    updated.put(routers.getJSONObject(j))
                                }
                            }

                            saveRouters(updated)
                            render()
                        }
                        .setNegativeButton("Batal", null)
                        .show()
                }
            }

            item.addView(deleteButton)
            root.addView(item, marginParams())
        }

        root.addView(
            makeText("PELANGGAN PPPoE", 21f, white, true),
            marginParams()
        )

        root.addView(
            makeText(
                "Data pelanggan akan ditampilkan setelah koneksi RouterOS API diaktifkan.",
                15f,
                gray
            )
        )
    }

    private fun addRouter() {

        val form = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(10), dp(20), dp(10))
        }

        val name = EditText(this).apply {
            hint = "Nama MikroTik"
            setSingleLine(true)
        }

        val ip = EditText(this).apply {
            hint = "Contoh: 192.168.1.150"
            setSingleLine(true)
            inputType = InputType.TYPE_CLASS_TEXT or
                InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD
            filters = arrayOf(InputFilter.LengthFilter(15))
        }

        val username = EditText(this).apply {
            hint = "Username MikroTik"
            setSingleLine(true)
        }

        val password = EditText(this).apply {
            hint = "Password MikroTik"
            setSingleLine(true)
            inputType = InputType.TYPE_CLASS_TEXT or
                InputType.TYPE_TEXT_VARIATION_PASSWORD
        }

        val port = EditText(this).apply {
            hint = "Port API"
            setText("8728")
            setSingleLine(true)
            inputType = InputType.TYPE_CLASS_NUMBER
        }

        form.addView(name)
        form.addView(ip)
        form.addView(username)
        form.addView(password)
        form.addView(port)

        val dialog = AlertDialog.Builder(this)
            .setTitle("Tambah MikroTik")
            .setView(form)
            .setPositiveButton("SIMPAN", null)
            .setNegativeButton("BATAL", null)
            .create()

        dialog.setOnShowListener {

            dialog.getButton(AlertDialog.BUTTON_POSITIVE)
                .setOnClickListener {

                    val n = name.text.toString().trim()
                    val address = ip.text.toString().trim()
                    val user = username.text.toString().trim()
                    val pass = password.text.toString()
                    val p = port.text.toString().trim()

                    if (n.isEmpty() ||
                        address.isEmpty() ||
                        user.isEmpty() ||
                        pass.isEmpty() ||
                        p.isEmpty()
                    ) {
                        Toast.makeText(
                            this,
                            "Lengkapi semua data",
                            Toast.LENGTH_SHORT
                        ).show()
                        return@setOnClickListener
                    }

                    if (!isValidIp(address)) {
                        Toast.makeText(
                            this,
                            "Format IP tidak valid",
                            Toast.LENGTH_SHORT
                        ).show()
                        return@setOnClickListener
                    }

                    val portNumber = p.toIntOrNull()

                    if (portNumber == null ||
                        portNumber !in 1..65535
                    ) {
                        Toast.makeText(
                            this,
                            "Port tidak valid",
                            Toast.LENGTH_SHORT
                        ).show()
                        return@setOnClickListener
                    }

                    val routers = loadRouters()

                    val router = JSONObject().apply {
                        put("name", n)
                        put("ip", address)
                        put("username", user)
                        put("password", pass)
                        put("port", p)
                    }

                    routers.put(router)
                    saveRouters(routers)

                    dialog.dismiss()
                    render()

                    Toast.makeText(
                        this,
                        "Router berhasil disimpan",
                        Toast.LENGTH_SHORT
                    ).show()
                }
        }

        dialog.show()
    }

    private fun isValidIp(ip: String): Boolean {

        val parts = ip.split(".")

        if (parts.size != 4) return false

        return parts.all {
            val number = it.toIntOrNull()
            number != null &&
                number in 0..255 &&
                it.isNotEmpty()
        }
    }
}
