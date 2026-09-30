package com.labrow.browser.core

import android.content.Context
import java.io.File

object StorageLayout {

    const val PROFILES_DIRECTORY = "profiles"
    const val SETTINGS_DIRECTORY = "settings"
    const val DIAGNOSTICS_DIRECTORY = "diagnostics"
    const val CACHE_DIRECTORY = "cache"
    const val INDEX_FILE = "index.json"

    fun profilesRoot(context: Context): File = File(context.filesDir, PROFILES_DIRECTORY)

    fun settingsRoot(context: Context): File = File(context.filesDir, SETTINGS_DIRECTORY)

    fun diagnosticsRoot(context: Context): File = File(context.filesDir, DIAGNOSTICS_DIRECTORY)

    fun cacheRoot(context: Context): File = File(context.cacheDir, CACHE_DIRECTORY)

    fun profileIndex(context: Context): File = File(profilesRoot(context), INDEX_FILE)

    fun profileFile(context: Context, profileId: String): File {
        require(PROFILE_ID_PATTERN.matches(profileId)) { "profile identifier is not valid" }
        return File(profilesRoot(context), "$profileId.json")
    }

    fun ensure(context: Context) {
        listOf(profilesRoot(context), settingsRoot(context), diagnosticsRoot(context)).forEach { directory ->
            if (!directory.exists()) {
                directory.mkdirs()
            }
        }
    }

    private val PROFILE_ID_PATTERN = Regex("^[a-z0-9][a-z0-9-]{0,62}$")
}
