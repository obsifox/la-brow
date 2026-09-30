package com.labrow.browser.core

import android.content.Context
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
        val runtime = runtime()
        preferences.forEach { entry ->
            when (entry.value) {
                is Boolean -> runtime.settings.setPref(entry.key, entry.value as Boolean)
                is Int -> runtime.settings.setPref(entry.key, entry.value as Int)
                is String -> runtime.settings.setPref(entry.key, entry.value as String)
            }
        }
    }

    fun applyDohSettings(enabled: Boolean, endpoint: String?) {
        val builder = runtime().settings
        builder.dnsOverHttpsEnabled = enabled
        if (endpoint != null) {
            builder.dnsOverHttpsUri = endpoint
        }
    }

    companion object {
        private var runtimeInstance: GeckoRuntime? = null
        const val GECKOVIEW_VERSION = "130.0.20240904133848"
    }
}
