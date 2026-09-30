package com.labrow.browser.core

import android.content.Context
import org.json.JSONObject
import java.io.BufferedReader
import java.io.File
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

class ApiException(message: String, val statusCode: Int) : Exception(message)

class ApiClient(private val context: Context) {

    var baseUrl: String = configuredBaseUrl()

    fun configuredBaseUrl(): String {
        val settings = File(StorageLayout.settingsRoot(context), APP_CONFIG_FILE)
        if (!settings.exists()) {
            return DEFAULT_BASE_URL
        }
        return JSONObject(settings.readText()).optString("api_base_url", DEFAULT_BASE_URL)
    }

    fun saveBaseUrl(value: String) {
        StorageLayout.ensure(context)
        val payload = JSONObject().put("api_base_url", value)
        File(StorageLayout.settingsRoot(context), APP_CONFIG_FILE).writeText(payload.toString(2))
        baseUrl = value
    }

    fun health(): JSONObject = request("/api/health", "GET", null)

    fun environment(address: String, profile: String, resolver: String, privacy: String, privateBrowsing: Boolean): JSONObject {
        val query = StringBuilder("/api/environment?")
        query.append("url=").append(encode(address))
        query.append("&profile=").append(encode(profile))
        query.append("&resolver=").append(encode(resolver))
        query.append("&privacy=").append(encode(privacy))
        query.append("&private=").append(if (privateBrowsing) "true" else "false")
        return request(query.toString(), "GET", null)
    }

    fun profiles(): JSONObject = request("/api/profiles", "GET", null)

    fun profile(profileId: String): JSONObject = request("/api/profiles/" + encode(profileId), "GET", null)

    fun saveProfile(profileId: String, profile: JSONObject): JSONObject {
        return request("/api/profiles/" + encode(profileId), "PUT", JSONObject().put("profile", profile))
    }

    fun deleteProfile(profileId: String): JSONObject = request("/api/profiles/" + encode(profileId), "DELETE", null)

    fun validateProfile(profile: JSONObject): JSONObject = request("/api/profiles/validate", "POST", JSONObject().put("profile", profile))

    fun diagnostics(level: String): JSONObject = request("/api/diagnostics?level=" + encode(level), "GET", null)

    fun dnsProbe(resolver: String, name: String, recordType: String): JSONObject {
        return request(
            "/api/dns/probe",
            "POST",
            JSONObject().put("resolver", resolver).put("name", name).put("type", recordType),
        )
    }

    fun scanState(): JSONObject = request("/api/scans", "GET", null)

    fun settings(): JSONObject = request("/api/settings", "GET", null)

    fun saveSettings(settings: JSONObject): JSONObject = request("/api/settings", "PUT", JSONObject().put("settings", settings))

    fun extensions(): JSONObject = request("/api/extensions", "GET", null)

    fun themes(): JSONObject = request("/api/themes", "GET", null)

    fun compatibilityMatrix(): JSONObject = request("/api/compat/firefox-desktop", "GET", null)

    fun inspectManifest(manifest: JSONObject): JSONObject = request("/api/extensions/inspect", "POST", JSONObject().put("manifest", manifest))

    fun installAddon(manifest: JSONObject, acknowledged: Boolean): JSONObject =
        request(
            "/api/extensions/install",
            "POST",
            JSONObject().put("manifest", manifest).put("acknowledged", acknowledged),
        )

    fun removeAddon(identifier: String): JSONObject = request("/api/extensions/" + encode(identifier), "DELETE", null)

    fun activateTheme(identifier: String): JSONObject = request("/api/themes/active", "PUT", JSONObject().put("id", identifier))

    private fun encode(value: String): String = URLEncoder.encode(value, "UTF-8")

    private fun request(path: String, method: String, body: JSONObject?): JSONObject {
        val connection = URL(baseUrl + path).openConnection() as HttpURLConnection
        connection.requestMethod = method
        connection.connectTimeout = CONNECT_TIMEOUT_MS
        connection.readTimeout = READ_TIMEOUT_MS
        connection.setRequestProperty("Accept", "application/json")
        if (body != null) {
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json")
            connection.outputStream.use { stream -> stream.write(body.toString().toByteArray()) }
        }
        val status = connection.responseCode
        val stream = if (status in 200..299) connection.inputStream else connection.errorStream
        val payload = stream?.let { readStream(it) } ?: "{}"
        connection.disconnect()
        val document = JSONObject(payload)
        if (status !in 200..299) {
            val message = document.optJSONObject("error")?.optString("message") ?: "request failed with status $status"
            throw ApiException(message, status)
        }
        return document
    }

    private fun readStream(stream: java.io.InputStream): String {
        val reader = BufferedReader(InputStreamReader(stream, Charsets.UTF_8))
        return reader.use { handle -> handle.readText() }
    }

    companion object {
        const val DEFAULT_BASE_URL = "http://10.0.2.2:8000"
        const val APP_CONFIG_FILE = "app.json"
        private const val CONNECT_TIMEOUT_MS = 8000
        private const val READ_TIMEOUT_MS = 20000
    }
}
