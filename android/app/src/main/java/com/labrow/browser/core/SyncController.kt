package com.labrow.browser.core

import org.json.JSONObject

class SyncResult(
    val status: String,
    val message: String,
    val document: EnvironmentDocument?,
)

class SyncController(private val context: Context) {

    private val client = ApiClient(context)

    fun baseUrl(): String = client.baseUrl

    fun setBaseUrl(value: String) {
        client.saveBaseUrl(value)
    }

    fun serverHealth(): SyncResult {
        return try {
            val payload = client.health()
            SyncResult("OK", "server version " + payload.optString("version"), null)
        } catch (error: Exception) {
            SyncResult("FAILED", error.message ?: "server unreachable", null)
        }
    }

    fun syncEnvironment(address: String, profileId: String, resolverId: String, privacyPreset: String, privateBrowsing: Boolean): SyncResult {
        return try {
            val payload = client.environment(address, profileId, resolverId, privacyPreset, privateBrowsing)
            val document = EnvironmentMapper.fromApiPayload(payload)
            persist(document)
            SyncResult("OK", "environment resolved by the application server", document)
        } catch (error: Exception) {
            SyncResult("FAILED", error.message ?: "environment request failed", null)
        }
    }

    fun probeResolver(resolverId: String, name: String, recordType: String): SyncResult {
        return try {
            val payload = client.dnsProbe(resolverId, name, recordType)
            val probe = payload.optJSONObject("probe") ?: JSONObject()
            val summary = probe.optString("status") + " " + probe.optString("rcode") + " " + probe.optDouble("latency_ms", 0.0) + " ms"
            SyncResult("OK", summary, null)
        } catch (error: Exception) {
            SyncResult("FAILED", error.message ?: "probe failed", null)
        }
    }

    fun exportDiagnostics(level: String): SyncResult {
        return try {
            val payload = client.diagnostics(level)
            val report = payload.optJSONObject("report") ?: JSONObject()
            val target = java.io.File(StorageLayout.diagnosticsRoot(context), "diagnostics-" + level + ".json")
            target.writeText(report.toString(2))
            SyncResult("OK", "redacted report written to " + target.name, null)
        } catch (error: Exception) {
            SyncResult("FAILED", error.message ?: "diagnostics export failed", null)
        }
    }

    private fun persist(document: EnvironmentDocument) {
        StorageLayout.ensure(context)
        val payload = JSONObject()
        payload.put("schema_version", document.schemaVersion)
        payload.put("generated_at", document.generatedAt)
        payload.put("status", document.status)
        payload.put("state", document.state)
        payload.put("active_profile", document.activeProfile)
        payload.put("webrtc_policy", document.webrtcPolicy)
        payload.put("privacy_preset", document.privacyPreset)
        document.location?.let { location ->
            val locationPayload = JSONObject()
            locationPayload.put("mode", location.mode)
            locationPayload.put("source", location.source)
            locationPayload.put("confidence", location.confidence)
            locationPayload.put("country", location.country ?: "")
            locationPayload.put("city", location.city ?: "")
            locationPayload.put("radius_m", location.radiusMeters)
            locationPayload.put("seed", location.seed ?: JSONObject.NULL)
            locationPayload.put("signals", org.json.JSONArray(location.signals))
            location.coordinate?.let { coordinate ->
                locationPayload.put(
                    "coordinate",
                    JSONObject()
                        .put("latitude", coordinate.latitude)
                        .put("longitude", coordinate.longitude)
                        .put("accuracy_m", coordinate.accuracyMeters),
                )
            }
            payload.put("location", locationPayload)
        }
        document.timezone?.let { zone ->
            payload.put(
                "timezone",
                JSONObject()
                    .put("zone", zone.zone)
                    .put("offset_minutes", zone.offsetMinutes)
                    .put("dst_active", zone.daylightSavingActive)
                    .put("controlled_surfaces", org.json.JSONArray(zone.controlledSurfaces))
                    .put("uncontrolled_surfaces", org.json.JSONArray(zone.uncontrolledSurfaces)),
            )
        }
        document.locale?.let { locale ->
            payload.put(
                "locale",
                JSONObject().put(
                    "surfaces",
                    JSONObject()
                        .put("browser_locale", locale.browserLocale)
                        .put("language_preference", locale.languagePreference)
                        .put("http_language_preference", locale.httpLanguagePreference)
                        .put("operating_system_locale", locale.operatingSystemLocale),
                ),
            )
        }
        document.dns?.let { dns ->
            payload.put(
                "dns",
                JSONObject()
                    .put("active_resolver", dns.resolverName)
                    .put("resolver_protocol", dns.protocol)
                    .put("endpoint", dns.endpoint)
                    .put("tls_status", dns.tlsStatus)
                    .put("fallback_state", dns.fallbackState)
                    .put("system_resolver_unchanged", dns.systemResolverUnchanged),
            )
        }
        val conflicts = org.json.JSONArray()
        document.conflicts.forEach { conflict ->
            conflicts.put(JSONObject().put("id", conflict.identifier).put("severity", conflict.severity).put("message", conflict.message))
        }
        payload.put("conflicts", conflicts)
        payload.put("notices", org.json.JSONArray(document.notices))
        java.io.File(StorageLayout.settingsRoot(context), EnvironmentRepository.ENVIRONMENT_FILE).writeText(payload.toString(2))
    }
}
