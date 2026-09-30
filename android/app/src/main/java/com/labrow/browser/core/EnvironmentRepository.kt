package com.labrow.browser.core

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class EnvironmentRepository(private val context: Context) {

    fun environmentDocument(): EnvironmentDocument? {
        val file = File(StorageLayout.settingsRoot(context), ENVIRONMENT_FILE)
        if (!file.exists()) {
            return null
        }
        val payload = JSONObject(file.readText())
        val conflicts = mutableListOf<EnvironmentConflict>()
        val conflictArray = payload.optJSONArray("conflicts") ?: JSONArray()
        for (position in 0 until conflictArray.length()) {
            val entry = conflictArray.getJSONObject(position)
            conflicts.add(
                EnvironmentConflict(
                    identifier = entry.optString("id"),
                    severity = entry.optString("severity"),
                    message = entry.optString("message"),
                ),
            )
        }
        val locationPayload = payload.optJSONObject("location")
        val coordinatePayload = locationPayload?.optJSONObject("coordinate")
        return EnvironmentDocument(
            schemaVersion = payload.optInt("schema_version", 1),
            generatedAt = payload.optString("generated_at"),
            status = payload.optString("status", "UNKNOWN"),
            state = payload.optString("state", "UNKNOWN"),
            activeProfile = payload.optString("active_profile", "default"),
            location = locationPayload?.let {
                EnvironmentLocation(
                    mode = it.optString("mode"),
                    source = it.optString("source"),
                    confidence = it.optDouble("confidence", 0.0),
                    country = it.optString("country").ifEmpty { null },
                    city = it.optString("city").ifEmpty { null },
                    radiusMeters = it.optDouble("radius_m", 0.0),
                    coordinate = coordinatePayload?.let { coordinate ->
                        EnvironmentCoordinate(
                            latitude = coordinate.optDouble("latitude"),
                            longitude = coordinate.optDouble("longitude"),
                            accuracyMeters = coordinate.optDouble("accuracy_m"),
                        )
                    },
                    seed = if (it.has("seed")) it.optLong("seed") else null,
                    signals = it.optJSONArray("signals")?.let { array -> (0 until array.length()).map { index -> array.getString(index) } } ?: emptyList(),
                )
            },
            timezone = payload.optJSONObject("timezone")?.let { zone ->
                EnvironmentTimezone(
                    zone = zone.optString("zone"),
                    offsetMinutes = zone.optInt("offset_minutes"),
                    daylightSavingActive = zone.optBoolean("dst_active"),
                    controlledSurfaces = zone.optJSONArray("controlled_surfaces")?.let { array -> (0 until array.length()).map { index -> array.getString(index) } } ?: emptyList(),
                    uncontrolledSurfaces = zone.optJSONArray("uncontrolled_surfaces")?.let { array -> (0 until array.length()).map { index -> array.getString(index) } } ?: emptyList(),
                )
            },
            locale = payload.optJSONObject("locale")?.let { localePayload ->
                val surfaces = localePayload.optJSONObject("surfaces") ?: JSONObject()
                EnvironmentLocale(
                    browserLocale = surfaces.optString("browser_locale"),
                    languagePreference = surfaces.optString("language_preference"),
                    httpLanguagePreference = surfaces.optString("http_language_preference"),
                    operatingSystemLocale = surfaces.optString("operating_system_locale"),
                )
            },
            dns = payload.optJSONObject("dns")?.let { dnsPayload ->
                EnvironmentDns(
                    resolverName = dnsPayload.optString("active_resolver"),
                    protocol = dnsPayload.optString("resolver_protocol"),
                    endpoint = dnsPayload.optString("endpoint"),
                    tlsStatus = dnsPayload.optString("tls_status"),
                    fallbackState = dnsPayload.optString("fallback_state"),
                    systemResolverUnchanged = dnsPayload.optBoolean("system_resolver_unchanged", true),
                )
            },
            webrtcPolicy = payload.optString("webrtc_policy", "default"),
            privacyPreset = payload.optString("privacy_preset", "balanced"),
            conflicts = conflicts,
            notices = payload.optJSONArray("notices")?.let { array -> (0 until array.length()).map { index -> array.getString(index) } } ?: emptyList(),
        )
    }

    fun networkState(): Map<String, String> {
        val manager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val active: Network? = manager.activeNetwork
        val capabilities = active?.let { manager.getNetworkCapabilities(it) }
        val transport = when {
            capabilities == null -> "unknown"
            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) -> "wifi"
            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> "cellular"
            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_VPN) -> "vpn"
            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET) -> "ethernet"
            else -> "other"
        }
        val metered = capabilities?.let { !it.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_METERED) } ?: false
        val vpnActive = capabilities?.hasTransport(NetworkCapabilities.TRANSPORT_VPN) ?: false
        return mapOf(
            "transport" to transport,
            "metered" to metered.toString(),
            "vpn_active" to vpnActive.toString(),
        )
    }

    fun pendingSessionTabs(): List<String> {
        val sessionFile = File(StorageLayout.settingsRoot(context), SESSION_FILE)
        if (!sessionFile.exists()) {
            return emptyList()
        }
        val payload = JSONObject(sessionFile.readText())
        val tabs = payload.optJSONArray("tabs") ?: JSONArray()
        return (0 until tabs.length()).map { position -> tabs.getJSONObject(position).optString("url") }
    }

    fun saveSession(urls: List<String>) {
        StorageLayout.ensure(context)
        val payload = JSONObject()
        payload.put("captured_at", java.time.Instant.now().toString())
        val tabs = JSONArray()
        urls.forEach { url -> tabs.put(JSONObject().put("url", url)) }
        payload.put("tabs", tabs)
        File(StorageLayout.settingsRoot(context), SESSION_FILE).writeText(payload.toString(2))
    }

    companion object {
        const val ENVIRONMENT_FILE = "environment.json"
        const val SESSION_FILE = "session.json"
    }
}
