package com.labrow.browser.core

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

class EnvironmentApiRepository(private val context: Context) {

    private val client = ApiClient(context)

    fun serverUrl(): String = client.baseUrl

    fun setServerUrl(value: String) {
        client.saveBaseUrl(value)
    }

    fun health(): String {
        val payload = client.health()
        return payload.optString("version") + " schema " + payload.optInt("profile_version") + " " + (payload.optJSONArray("capabilities")?.length() ?: 0) + " capabilities"
    }

    fun resolve(address: String, profile: String, resolver: String, privacy: String, privateBrowsing: Boolean): EnvironmentDocument {
        val payload = client.environment(address, profile, resolver, privacy, privateBrowsing)
        val document = EnvironmentMapper.fromApiPayload(payload)
        val theme = ExtensionRepository(context).activeTheme()
        ThemeEngine.persist(context, theme)
        return document
    }

    fun profileIdentifiers(): List<String> {
        val payload = client.profiles()
        val entries = payload.optJSONArray("profiles") ?: JSONArray()
        return (0 until entries.length()).map { index -> entries.optJSONObject(index)?.optString("id") ?: "default" }
    }

    fun resolverIdentifiers(): List<String> {
        val payload = client.resolvers()
        val entries = payload.optJSONArray("resolvers") ?: JSONArray()
        return (0 until entries.length()).map { index -> entries.optJSONObject(index)?.optString("id") ?: "system" }
    }

    fun profile(identifier: String): JSONObject = client.profile(identifier)

    fun saveProfile(identifier: String, profile: JSONObject): JSONObject = client.saveProfile(identifier, profile)

    fun deleteProfile(identifier: String): JSONObject = client.deleteProfile(identifier)

    fun validateProfile(profile: JSONObject): JSONObject = client.validateProfile(profile)

    fun probe(resolver: String, name: String, recordType: String): JSONObject = client.dnsProbe(resolver, name, recordType)

    fun diagnostics(level: String): JSONObject = client.diagnostics(level)

    fun settings(): JSONObject = client.settings()

    fun saveSettings(settings: JSONObject): JSONObject = client.saveSettings(settings)

    fun scanState(): JSONObject = client.scanState()
}
