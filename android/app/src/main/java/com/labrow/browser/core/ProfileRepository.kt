package com.labrow.browser.core

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

class ProfileValidationException(message: String) : Exception(message)

class ProfileRepository(private val context: Context) {

    fun listProfiles(): List<JSONObject> {
        val indexFile = StorageLayout.profileIndex(context)
        if (!indexFile.exists()) {
            return emptyList()
        }
        val index = JSONObject(indexFile.readText())
        val entries = index.optJSONArray("profiles") ?: JSONArray()
        return (0 until entries.length()).map { position -> entries.getJSONObject(position) }
    }

    fun readProfile(profileId: String): JSONObject {
        val file = StorageLayout.profileFile(context, profileId)
        if (!file.exists()) {
            throw ProfileValidationException("profile was not found")
        }
        val payload = JSONObject(file.readText())
        return payload.optJSONObject("profile") ?: payload
    }

    fun validate(profile: JSONObject): List<String> {
        val problems = mutableListOf<String>()
        val version = profile.optInt("profile_version", -1)
        if (version !in SUPPORTED_VERSIONS) {
            problems.add("unsupported profile version")
        }
        val latitude = profile.opt("latitude")
        val longitude = profile.opt("longitude")
        if ((latitude == null) != (longitude == null)) {
            problems.add("latitude and longitude must be provided together")
        }
        if (latitude is Number && (latitude.toDouble() < -90.0 || latitude.toDouble() > 90.0)) {
            problems.add("latitude is out of range")
        }
        if (longitude is Number && (longitude.toDouble() < -180.0 || longitude.toDouble() > 180.0)) {
            problems.add("longitude is out of range")
        }
        val radius = profile.opt("radius")
        if (radius is Number && radius.toDouble() < 0.0) {
            problems.add("radius must not be negative")
        }
        val mode = profile.optString("geolocation_mode", "manual")
        if (mode !in SUPPORTED_MODES) {
            problems.add("unsupported geolocation mode")
        }
        return problems
    }

    fun importProfile(profileId: String, payload: String, dryRun: Boolean): JSONObject {
        val document = JSONObject(payload)
        val profile = document.optJSONObject("profile") ?: document
        val problems = validate(profile)
        if (problems.isNotEmpty()) {
            throw ProfileValidationException(problems.joinToString("; "))
        }
        val result = JSONObject()
        result.put("validated", true)
        result.put("dry_run", dryRun)
        if (!dryRun) {
            StorageLayout.ensure(context)
            val target = StorageLayout.profileFile(context, profileId)
            target.writeText(document.toString(2))
            result.put("activated", true)
            result.put("path", target.absolutePath)
        } else {
            result.put("activated", false)
        }
        return result
    }

    fun exportProfile(profileId: String): String {
        val profile = readProfile(profileId)
        val document = JSONObject()
        document.put("profile", profile)
        document.put("exported_at", java.time.Instant.now().toString())
        return document.toString(2)
    }

    companion object {
        val SUPPORTED_VERSIONS = setOf(1, 2)
        val SUPPORTED_MODES = setOf("disabled", "manual", "automatic", "hybrid")
    }
}
