package com.labrow.browser.core

import android.content.Context
import org.mozilla.geckoview.GeckoPreferenceController
import org.mozilla.geckoview.GeckoResult
import org.mozilla.geckoview.GeckoRuntime
import org.mozilla.geckoview.GeckoRuntimeSettings
import org.mozilla.geckoview.GeckoSession
import org.mozilla.geckoview.GeckoSessionSettings

class GeckoRuntimeHolder(private val context: Context) {

    fun runtime(): GeckoRuntime {
        if (runtimeInstance == null) {
            val settings = GeckoRuntimeSettings.Builder()
                .aboutConfigEnabled(true)
                .javaScriptEnabled(true)
                .remoteDebuggingEnabled(false)
                .build()
            runtimeInstance = GeckoRuntime.create(context, settings)
        }
        return runtimeInstance as GeckoRuntime
    }

    fun session(privateBrowsing: Boolean): GeckoSession {
        val settings = GeckoSessionSettings.Builder()
            .usePrivateMode(privateBrowsing)
            .useTrackingProtection(true)
            .suspendMediaWhenInactive(true)
            .build()
        val session = GeckoSession(settings)
        session.open(runtime())
        return session
    }

    fun applyEnvironmentPreferences(preferences: Map<String, Any>) {
        runtime()
        preferences.forEach { entry ->
            val result: GeckoResult<Void>? = when (val value = entry.value) {
                is Boolean -> GeckoPreferenceController.setGeckoPref(entry.key, value, GeckoPreferenceController.PREF_BRANCH_USER)
                is Int -> GeckoPreferenceController.setGeckoPref(entry.key, value, GeckoPreferenceController.PREF_BRANCH_USER)
                is String -> GeckoPreferenceController.setGeckoPref(entry.key, value, GeckoPreferenceController.PREF_BRANCH_USER)
                else -> null
            }
            if (result != null) {
                pendingPreferences.add(result)
            }
        }
    }

    fun applyDohSettings(enabled: Boolean, endpoint: String?) {
        val settings = runtime().settings
        if (!enabled) {
            settings.setTrustedRecursiveResolverMode(GeckoRuntimeSettings.TRR_MODE_OFF)
            settings.setDohAutoselectEnabled(false)
            return
        }
        settings.setTrustedRecursiveResolverMode(GeckoRuntimeSettings.TRR_MODE_FIRST)
        settings.setDohAutoselectEnabled(false)
        if (endpoint != null) {
            settings.setTrustedRecursiveResolverUri(endpoint)
        }
    }

    private val pendingPreferences = mutableListOf<GeckoResult<Void>>()

    companion object {
        private var runtimeInstance: GeckoRuntime? = null
        const val GECKOVIEW_VERSION = "153.0.20260810162159"
    }
}
