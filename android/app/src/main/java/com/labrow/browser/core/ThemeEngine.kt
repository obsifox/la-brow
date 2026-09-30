package com.labrow.browser.core

import android.content.Context
import android.graphics.Color
import androidx.compose.ui.graphics.Color as ComposeColor
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

object ThemeEngine {

    const val THEME_FILE = "theme.json"

    val productStops: List<ComposeColor> = listOf(
        ComposeColor(0xFF0B0C0E),
        ComposeColor(0xFF1B0B2E),
        ComposeColor(0xFFFF2D3F),
    )

    private fun parse(value: String?): ComposeColor? {
        if (value.isNullOrBlank()) {
            return null
        }
        return try {
            ComposeColor(android.graphics.Color.parseColor(value))
        } catch (error: IllegalArgumentException) {
            null
        }
    }

    fun stopsFrom(theme: GameTheme?): List<ComposeColor> {
        val parsed = theme?.stops?.mapNotNull { stop -> parse(stop) } ?: emptyList()
        return if (parsed.size >= 2) parsed else productStops
    }

    fun accentFrom(theme: GameTheme?): ComposeColor = parse(theme?.accent) ?: ComposeColor(0xFFA855F7)

    fun themeFromSpec(payload: JSONObject?): GameTheme? {
        if (payload == null) {
            return null
        }
        val gradient = payload.optJSONObject("gradient") ?: return null
        val stopArray = gradient.optJSONArray("stops") ?: JSONArray()
        val stops = (0 until stopArray.length()).map { index -> stopArray.optString(index) }
        val palettePayload = payload.optJSONObject("palette") ?: JSONObject()
        val palette = mutableMapOf<String, String>()
        val keys = palettePayload.keys()
        while (keys.hasNext()) {
            val key = keys.next()
            palette[key] = palettePayload.optString(key)
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
        val images = payload.optJSONObject("images")
        return GameTheme(
            id = payload.optString("id"),
            name = payload.optString("name"),
            source = payload.optString("source"),
            compositionLevel = payload.optString("runtime_compatibility", "PARTIAL"),
            stops = stops,
            accent = gradient.optString("accent"),
            accentGlow = gradient.optString("accent_glow"),
            palette = palette,
            findings = parsedFindings,
            frameImage = images?.optString("theme_frame"),
        )
    }

    fun persist(context: Context, theme: GameTheme?) {
        val target = File(StorageLayout.settingsRoot(context), THEME_FILE)
        if (theme == null) {
            target.delete()
            return
        }
        val palette = JSONObject()
        for (entry in theme.palette) {
            palette.put(entry.key, entry.value)
        }
        val payload = JSONObject()
            .put("id", theme.id)
            .put("name", theme.name)
            .put("source", theme.source)
            .put("stops", JSONArray(theme.stops))
            .put("accent", theme.accent)
            .put("accent_glow", theme.accentGlow)
            .put("palette", palette)
        target.writeText(payload.toString(2))
    }

    fun restore(context: Context): GameTheme? {
        val source = File(StorageLayout.settingsRoot(context), THEME_FILE)
        if (!source.exists()) {
            return null
        }
        return try {
            val payload = JSONObject(source.readText())
            val gradient = JSONObject()
                .put("stops", payload.optJSONArray("stops") ?: JSONArray())
                .put("accent", payload.optString("accent"))
                .put("accent_glow", payload.optString("accent_glow"))
            themeFromSpec(
                JSONObject()
                    .put("id", payload.optString("id"))
                    .put("name", payload.optString("name"))
                    .put("source", payload.optString("source"))
                    .put("gradient", gradient)
                    .put("palette", payload.optJSONObject("palette") ?: JSONObject()),
            )
        } catch (error: Exception) {
            null
        }
    }

    fun contrastRatio(first: String, second: String): Double {
        val left = luminance(parse(first) ?: return 1.0) + 0.05
        val right = luminance(parse(second) ?: return 1.0) + 0.05
        return if (left > right) left / right else right / left
    }

    private fun luminance(color: ComposeColor): Double {
        val channels = listOf(color.red.toDouble(), color.green.toDouble(), color.blue.toDouble())
        val linear = channels.map { channel ->
            if (channel <= 0.03928) channel / 12.92 else Math.pow((channel + 0.055) / 1.055, 2.4)
        }
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    }

    fun legacyColor(value: String): Int = try {
        Color.parseColor(value)
    } catch (error: IllegalArgumentException) {
        Color.BLACK
    }
}
