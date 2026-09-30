package com.labrow.browser.core

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

class DnsRepository(private val context: Context) {

    fun resolverProfiles(): List<JSONObject> {
        val resource = context.resources.openRawResource(context.resources.getIdentifier("dns_providers", "raw", context.packageName))
        val payload = JSONObject(resource.bufferedReader().readText())
        val providers = payload.optJSONArray("providers") ?: JSONArray()
        return (0 until providers.length()).map { position -> providers.getJSONObject(position) }
    }

    fun activeResolver(): JSONObject {
        val settings = StorageLayout.settingsRoot(context)
        val settingsFile = java.io.File(settings, "settings.json")
        if (!settingsFile.exists()) {
            return JSONObject().put("id", "system").put("protocol", "system")
        }
        val payload = JSONObject(settingsFile.readText())
        return payload.optJSONObject("resolver") ?: JSONObject().put("id", "system").put("protocol", "system")
    }

    fun diagnosticsSnapshot(): JSONObject {
        val resolver = activeResolver()
        val payload = JSONObject()
        payload.put("resolver", resolver)
        payload.put("system_resolver_unchanged", true)
        payload.put("browser_scoped", true)
        payload.put("statement", "Browser DNS configuration does not modify device or network resolver settings.")
        return payload
    }
}
