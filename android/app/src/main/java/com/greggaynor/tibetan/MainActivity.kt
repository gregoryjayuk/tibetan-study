package com.greggaynor.tibetan

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import org.json.JSONArray

/**
 * The study app on the phone. The screens are the same page the desktop server shows (app/index.html
 * in the data folder), so when that folder is synced, an update reaches the phone with no reinstall.
 * This shell only gives that page a way to read the folder and save progress into it.
 */
class MainActivity : Activity() {
    private lateinit var web: WebView
    private var folder: Folder? = null
    private var pausedAt = 0L
    private val prefs by lazy { getSharedPreferences("tibetan", MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = Color.parseColor("#1c1a17")
        window.navigationBarColor = Color.parseColor("#26231f")
        web = WebView(this)
        web.setBackgroundColor(Color.parseColor("#1c1a17"))
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        web.settings.allowFileAccess = false
        web.webViewClient = WebViewClient()
        web.webChromeClient = WebChromeClient() // lets confirm() dialogs show
        web.addJavascriptInterface(Bridge(), "TibetanBridge")
        setContentView(web)

        val saved = prefs.getString("tree", null)?.let(Uri::parse)
        if (saved != null && hasAccess(saved)) {
            folder = Folder(this, saved)
            loadApp()
        } else {
            pick()
        }
    }

    private fun hasAccess(u: Uri) =
        contentResolver.persistedUriPermissions.any { it.uri == u && it.isReadPermission && it.isWritePermission }

    private fun pick() {
        Toast.makeText(this, "Choose your Tibetan data folder (the one with app/ inside)", Toast.LENGTH_LONG).show()
        val i = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE)
        i.addFlags(
            Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION or
                Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION
        )
        @Suppress("DEPRECATION")
        startActivityForResult(i, PICK)
    }

    @Deprecated("framework Activity result")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        @Suppress("DEPRECATION")
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != PICK) return
        val u = data?.data
        if (resultCode == RESULT_OK && u != null) {
            contentResolver.takePersistableUriPermission(
                u, Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
            )
            prefs.edit().putString("tree", u.toString()).apply()
            folder = Folder(this, u)
        }
        loadApp()
    }

    private fun loadApp() {
        val html = try { folder?.read("app/index.html") } catch (e: Exception) { null }
            ?: assets.open("index.html").bufferedReader().use { it.readText() }
        web.loadDataWithBaseURL("https://tibetan.app/", html, "text/html", "UTF-8", null)
    }

    override fun onPause() {
        super.onPause()
        pausedAt = System.currentTimeMillis()
    }

    override fun onResume() {
        super.onResume()
        // back after a while: reload, to pick up new class notes and the Mac's progress
        if (pausedAt > 0 && System.currentTimeMillis() - pausedAt > 10 * 60 * 1000) loadApp()
    }

    @Deprecated("framework back handling")
    override fun onBackPressed() {
        web.evaluateJavascript("window.onAndroidBack ? window.onAndroidBack() : 'exit'") { r ->
            if (r == null || r.contains("exit")) finish()
        }
    }

    inner class Bridge {
        @JavascriptInterface
        fun device(): String = prefs.getString("device", "phone") ?: "phone"

        @JavascriptInterface
        fun read(path: String): String = try { folder?.read(path) ?: "" } catch (e: Exception) { "" }

        @JavascriptInterface
        fun list(dir: String): String =
            try { JSONArray(folder?.list(dir) ?: emptyList<String>()).toString() } catch (e: Exception) { "[]" }

        @JavascriptInterface
        fun append(path: String, text: String): String {
            if (path != "progress/${device()}.jsonl") return "denied"
            return try { if (folder?.append(path, text) == true) "ok" else "fail" } catch (e: Exception) { "fail" }
        }

        @JavascriptInterface
        fun write(path: String, text: String): String {
            if (!(path.startsWith("inbox/") && path.endsWith(".txt") && path.count { it == '/' } == 1)) return "denied"
            return try { if (folder?.create(path, text) == true) "ok" else "fail" } catch (e: Exception) { "fail" }
        }

        @JavascriptInterface
        fun pickFolder() { runOnUiThread { pick() } }

        @JavascriptInterface
        fun reload() { runOnUiThread { loadApp() } }
    }

    companion object {
        const val PICK = 7
    }
}
