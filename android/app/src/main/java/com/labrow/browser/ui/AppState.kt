package com.labrow.browser.ui

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.labrow.browser.core.AddonInspection
import com.labrow.browser.core.CompatibilityItem
import com.labrow.browser.core.EnvironmentApiRepository
import com.labrow.browser.core.EnvironmentDocument
import com.labrow.browser.core.EnvironmentMapper
import com.labrow.browser.core.EnvironmentRepository
import com.labrow.browser.core.ExtensionRepository
import com.labrow.browser.core.GameTheme
import com.labrow.browser.core.InstalledAddon
import com.labrow.browser.core.ThemeEngine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

class AppState(val context: Context) {

    private val environmentApi = EnvironmentApiRepository(context)
    private val extensionRepository = ExtensionRepository(context)

    var serverUrl by mutableStateOf(environmentApi.serverUrl())
    var healthLine by mutableStateOf("connecting to the application server")
    var statusLine by mutableStateOf("idle")
    var environment by mutableStateOf<EnvironmentDocument?>(EnvironmentRepository(context).environmentDocument())
    var theme by mutableStateOf<GameTheme?>(ThemeEngine.restore(context))
    var inspection by mutableStateOf<AddonInspection?>(null)
    var notice by mutableStateOf("")
    var diagnostics by mutableStateOf("no report generated yet")
    var scanSummary by mutableStateOf("not requested")
    var probeSummary by mutableStateOf("no probe run yet")
    var profileDraft by mutableStateOf("")
    var validationSummary by mutableStateOf("no validation run yet")
    var lastError by mutableStateOf("")
    var busy by mutableStateOf(false)

    val addons = mutableStateListOf<InstalledAddon>()
    val matrix = mutableStateListOf<CompatibilityItem>()
    val profiles = mutableStateListOf<String>()
    val resolvers = mutableStateListOf<String>()

    fun updateServer(value: String) {
        environmentApi.setServerUrl(value)
        serverUrl = environmentApi.serverUrl()
    }

    suspend fun refreshHealth() = guard("health") {
        healthLine = environmentApi.health()
        statusLine = "server connected"
    }

    suspend fun resolve(address: String, profile: String, resolver: String, privacy: String, privateBrowsing: Boolean) = guard("resolve") {
        environment = environmentApi.resolve(address, profile, resolver, privacy, privateBrowsing)
        statusLine = "environment resolved"
    }

    suspend fun loadProfiles() = guard("profiles") {
        profiles.clear()
        profiles.addAll(environmentApi.profileIdentifiers())
    }

    suspend fun loadResolvers() = guard("resolvers") {
        resolvers.clear()
        resolvers.addAll(environmentApi.resolverIdentifiers())
    }

    suspend fun loadProfileDraft(identifier: String) = guard("profile") {
        profileDraft = environmentApi.profile(identifier).optJSONObject("profile")?.toString(2) ?: "{}"
    }

    suspend fun saveProfileDraft(identifier: String) = guard("profile") {
        environmentApi.saveProfile(identifier, JSONObject(profileDraft))
        profiles.clear()
        profiles.addAll(environmentApi.profileIdentifiers())
        statusLine = "profile saved"
    }

    suspend fun validateDraft() = guard("validate") {
        val payload = environmentApi.validateProfile(JSONObject(profileDraft))
        validationSummary = payload.toString(2)
        statusLine = "profile validated"
    }

    suspend fun deleteProfile(identifier: String) = guard("delete") {
        environmentApi.deleteProfile(identifier)
        profiles.clear()
        profiles.addAll(environmentApi.profileIdentifiers())
        statusLine = "profile deleted"
    }

    suspend fun runProbe(resolver: String, name: String, recordType: String) = guard("probe") {
        val payload = environmentApi.probe(resolver, name, recordType)
        val probe = payload.optJSONObject("probe") ?: payload
        probeSummary = "status " + probe.optString("status") + " rcode " + probe.optString("rcode") + " latency " + probe.optDouble("latency_ms", 0.0) + " ms"
        statusLine = "resolver probe completed"
    }

    suspend fun loadDiagnostics(level: String) = guard("diagnostics") {
        val payload = environmentApi.diagnostics(level)
        diagnostics = payload.toString(2)
        statusLine = "diagnostic report generated at " + level + " level"
    }

    suspend fun loadScans() = guard("scans") {
        val payload = environmentApi.scanState()
        scanSummary = payload.toString(2)
        statusLine = "policy scan state refreshed"
    }

    suspend fun loadAddons() = guard("addons") {
        addons.clear()
        addons.addAll(extensionRepository.installed())
        notice = extensionRepository.notice()
        statusLine = "add-on registry refreshed"
    }

    suspend fun loadMatrix() = guard("matrix") {
        matrix.clear()
        matrix.addAll(extensionRepository.matrix())
    }

    suspend fun inspectManifest(text: String) = guard("inspect") {
        inspection = extensionRepository.inspect(manifest(text))
        statusLine = "manifest inspected"
    }

    suspend fun installManifest(text: String, acknowledged: Boolean) = guard("install") {
        extensionRepository.install(manifest(text), acknowledged)
        addons.clear()
        addons.addAll(extensionRepository.installed())
        theme = extensionRepository.activeTheme() ?: theme
        statusLine = "add-on recorded, compatibility notice acknowledged"
    }

    suspend fun removeAddon(identifier: String) = guard("remove") {
        extensionRepository.remove(identifier)
        addons.clear()
        addons.addAll(extensionRepository.installed())
        statusLine = "add-on removed"
    }

    suspend fun activateTheme(identifier: String) = guard("theme") {
        theme = extensionRepository.activateTheme(identifier)
        statusLine = "theme activated"
    }

    suspend fun refreshTheme() = guard("theme") {
        theme = extensionRepository.activeTheme()
    }

    suspend fun saveServerSettings(defaultUrl: String, privacy: String, level: String, privateBrowsing: Boolean) = guard("settings") {
        val settings = JSONObject()
            .put("default_url", defaultUrl)
            .put("privacy_preset", privacy)
            .put("diagnostics_level", level)
            .put("private_browsing", privateBrowsing)
            .put("active_profile", "default")
            .put("resolver_profile", "system")
        environmentApi.saveSettings(settings)
        statusLine = "settings saved on the server"
    }

    suspend fun loadServerSettings() = guard("settings") {
        profileDraft = environmentApi.settings().toString(2)
    }

    private fun manifest(text: String): JSONObject = JSONObject(text)

    private suspend fun guard(label: String, block: suspend () -> Unit) {
        busy = true
        statusLine = label + " in progress"
        try {
            withContext(Dispatchers.IO) { block() }
            lastError = ""
        } catch (error: Exception) {
            lastError = error.message ?: (label + " failed")
            statusLine = label + " failed"
        } finally {
            busy = false
        }
    }
}
