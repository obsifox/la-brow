package com.labrow.browser.core

import org.json.JSONArray
import org.json.JSONObject

object EnvironmentMapper {

    fun fromApiPayload(payload: JSONObject): EnvironmentDocument {
        val snapshot = payload.optJSONObject("snapshot") ?: JSONObject()
        val profile = snapshot.optJSONObject("effective_profile") ?: JSONObject()
        val geo = snapshot.optJSONObject("geo")
        val coordinatePayload = geo?.optJSONObject("coordinate")
        val timezonePayload = snapshot.optJSONObject("timezone")
        val localePayload = snapshot.optJSONObject("locale")?.optJSONObject("surfaces")
        val dnsPayload = snapshot.optJSONObject("dns")
        val privacyPayload = snapshot.optJSONObject("privacy")
        val consistency = snapshot.optJSONObject("consistency")
        val geoEngine = snapshot.optJSONObject("geo_engine")
        val stages = snapshot.optJSONArray("stages") ?: JSONArray()
        val conflicts = mutableListOf<EnvironmentConflict>()
        consistency?.optJSONArray("findings")?.let { findings ->
            for (position in 0 until findings.length()) {
                val entry = findings.getJSONObject(position)
                conflicts.add(
                    EnvironmentConflict(
                        identifier = entry.optString("id"),
                        severity = entry.optString("severity"),
                        message = entry.optString("message"),
                    ),
                )
            }
        }
        var satisfiedInvariants = 0
        val stageList = (0 until stages.length()).map { index ->
            val stage = stages.optJSONObject(index) ?: JSONObject()
            if (stage.optString("stage") == INVARIANTS_STAGE) {
                val invariants = stage.optJSONObject("output")?.optJSONArray("invariants")
                if (invariants != null) {
                    for (position in 0 until invariants.length()) {
                        if (invariants.optJSONObject(position)?.optBoolean("satisfied", false) == true) {
                            satisfiedInvariants += 1
                        }
                    }
                }
            }
            EnvironmentStage(
                name = stage.optString("stage"),
                status = stage.optString("status"),
                detail = stage.optString("detail"),
            )
        }
        return EnvironmentDocument(
            schemaVersion = 1,
            generatedAt = payload.optString("generated_at"),
            status = snapshot.optString("status", "UNKNOWN"),
            state = snapshot.optJSONObject("state")?.optString("state") ?: "UNKNOWN",
            activeProfile = profile.optString("name", "default"),
            location = geo?.let {
                EnvironmentLocation(
                    mode = it.optString("mode"),
                    source = it.optString("source"),
                    confidence = it.optDouble("confidence", 0.0),
                    country = profile.optString("country").ifEmpty { null },
                    city = profile.optString("city").ifEmpty { null },
                    radiusMeters = profile.optDouble("radius", 0.0),
                    coordinate = coordinatePayload?.let { coordinate ->
                        EnvironmentCoordinate(
                            latitude = coordinate.optDouble("latitude"),
                            longitude = coordinate.optDouble("longitude"),
                            accuracyMeters = coordinate.optDouble("accuracy_m"),
                        )
                    },
                    seed = if (it.has("seed") && !it.isNull("seed")) it.optLong("seed") else null,
                    signals = stringList(it.optJSONArray("signals")),
                )
            },
            timezone = timezonePayload?.let { zone ->
                EnvironmentTimezone(
                    zone = zone.optString("zone"),
                    offsetMinutes = zone.optInt("offset_minutes"),
                    daylightSavingActive = zone.optBoolean("dst_active"),
                    controlledSurfaces = stringList(zone.optJSONArray("controlled_surfaces")),
                    uncontrolledSurfaces = stringList(zone.optJSONArray("uncontrolled_surfaces")),
                )
            },
            locale = localePayload?.let { surfaces ->
                EnvironmentLocale(
                    browserLocale = surfaces.optString("browser_locale"),
                    languagePreference = surfaces.optString("language_preference"),
                    httpLanguagePreference = surfaces.optString("http_language_preference"),
                    operatingSystemLocale = surfaces.optString("operating_system_locale"),
                )
            },
            dns = dnsPayload?.let { dns ->
                EnvironmentDns(
                    resolverName = dns.optString("active_resolver"),
                    protocol = dns.optString("resolver_protocol"),
                    endpoint = dns.optString("endpoint"),
                    tlsStatus = dns.optString("tls_status"),
                    fallbackState = dns.optString("fallback_state"),
                    systemResolverUnchanged = dns.optBoolean("system_resolver_unchanged", true),
                )
            },
            webrtcPolicy = privacyPayload?.optJSONObject("policy")?.optString("webrtc_policy")
                ?: profile.optString("webrtc_policy", "default"),
            privacyPreset = privacyPayload?.optString("preset", "balanced") ?: "balanced",
            privateBrowsing = privacyPayload?.optBoolean("private_browsing", false)
                ?: snapshot.optBoolean("private_browsing", false),
            conflicts = conflicts,
            stages = stageList,
            invariantCount = satisfiedInvariants,
            geoState = geoEngine?.optJSONObject("state")?.optString("state", "UNKNOWN") ?: "UNKNOWN",
            notices = listOf(
                "Environment controls do not guarantee anonymity and do not change the public IP address observed by websites.",
                "Browser DNS configuration never modifies device or network DNS settings.",
            ),
        )
    }

    private const val INVARIANTS_STAGE = "web_content_ready"

    private fun stringList(array: JSONArray?): List<String> {
        if (array == null) {
            return emptyList()
        }
        return (0 until array.length()).map { position -> array.getString(position) }
    }
}
