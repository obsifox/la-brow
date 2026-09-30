package com.labrow.browser.core

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

class ExtensionRepository(private val context: Context) {

    private val client = ApiClient(context)

    fun installed(): List<InstalledAddon> {
        val payload = client.extensions()
        val entries = payload.optJSONArray("extensions") ?: JSONArray()
        return (0 until entries.length()).map { index ->
            val entry = entries.optJSONObject(index) ?: JSONObject()
            InstalledAddon(
                id = entry.optString("id"),
                name = entry.optString("name"),
                version = entry.optString("version"),
                type = entry.optString("type"),
                compatibilityLevel = entry.optString("compatibility_level"),
                compatibilityScore = entry.optDouble("compatibility_score", 0.0),
                signature = entry.optString("signature"),
                noticeAcknowledged = entry.optBoolean("notice_acknowledged", false),
                installedAt = entry.optString("installed_at"),
            )
        }
    }

    fun notice(): String = client.extensions().optString("notice")

    fun matrix(): List<CompatibilityItem> {
        val payload = client.compatibilityMatrix()
        val sections = payload.optJSONArray("sections") ?: JSONArray()
        return (0 until sections.length()).map { index ->
            val entry = sections.optJSONObject(index) ?: JSONObject()
            CompatibilityItem(
                surface = entry.optString("section"),
                level = entry.optString("level"),
                note = entry.optString("note"),
            )
        }
    }

    fun inspect(manifest: JSONObject): AddonInspection {
        val payload = client.inspectManifest(manifest)
        return AddonInspection(
            manifestName = payload.optJSONObject("manifest")?.optString("name") ?: "",
            manifestType = payload.optJSONObject("manifest")?.optString("type") ?: "extension",
            report = report(payload.optJSONObject("compatibility")),
            theme = ThemeEngine.themeFromSpec(payload.optJSONObject("theme")),
            previewCode = payload.optJSONObject("install_preview")?.optString("code") ?: "",
        )
    }

    fun install(manifest: JSONObject, acknowledged: Boolean): InstalledAddon {
        val payload = client.installAddon(manifest, acknowledged)
        val record = payload.optJSONObject("installed") ?: JSONObject()
        return InstalledAddon(
            id = record.optString("id"),
            name = record.optString("name"),
            version = record.optString("version"),
            type = record.optString("type"),
            compatibilityLevel = record.optString("compatibility_level"),
            compatibilityScore = record.optDouble("compatibility_score", 0.0),
            signature = record.optString("signature"),
            noticeAcknowledged = record.optBoolean("notice_acknowledged", false),
            installedAt = record.optString("installed_at"),
        )
    }

    fun remove(identifier: String): Boolean = client.removeAddon(identifier).optBoolean("removed", false)

    fun activateTheme(identifier: String): GameTheme? {
        val payload = client.activateTheme(identifier)
        val theme = ThemeEngine.themeFromSpec(payload.optJSONObject("theme"))
        ThemeEngine.persist(context, theme)
        return theme
    }

    fun activeTheme(): GameTheme? {
        val payload = client.themes()
        val theme = ThemeEngine.themeFromSpec(payload.optJSONObject("active_theme"))
        if (theme != null) {
            ThemeEngine.persist(context, theme)
            return theme
        }
        return ThemeEngine.restore(context)
    }

    private fun report(payload: JSONObject?): CompatibilityReport {
        if (payload == null) {
            return CompatibilityReport("UNKNOWN", 0.0, emptyList(), emptyList(), emptyList(), "", "geckoview")
        }
        fun items(key: String, surfaceKey: String): List<CompatibilityItem> {
            val array = payload.optJSONArray(key) ?: JSONArray()
            return (0 until array.length()).map { index ->
                val entry = array.optJSONObject(index) ?: JSONObject()
                CompatibilityItem(
                    surface = entry.optString(surfaceKey),
                    level = entry.optString("level"),
                    note = entry.optString("note"),
                )
            }
        }
        val findings = payload.optJSONArray("findings") ?: JSONArray()
        val parsedFindings = (0 until findings.length()).map { index ->
            val entry = findings.optJSONObject(index) ?: JSONObject()
            CompatibilityFinding(
                code = entry.optString("code"),
                severity = entry.optString("severity"),
                message = entry.optString("message"),
                detail = entry.optString("detail"),
            )
        }
        return CompatibilityReport(
            level = payload.optString("level"),
            score = payload.optDouble("score", 0.0),
            sections = items("sections", "section"),
            permissions = items("permissions", "permission"),
            findings = parsedFindings,
            notice = payload.optString("notice"),
            runtimeEngine = payload.optJSONObject("runtime")?.optString("engine") ?: "geckoview",
        )
    }
}
