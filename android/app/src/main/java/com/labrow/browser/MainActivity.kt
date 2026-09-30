package com.labrow.browser

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.labrow.browser.core.EnvironmentDocument
import com.labrow.browser.core.EnvironmentRepository
import com.labrow.browser.core.GeckoRuntimeHolder
import com.labrow.browser.core.StorageLayout
import com.labrow.browser.core.SyncController
import com.labrow.browser.core.SyncResult
import com.labrow.browser.ui.ControlCenterScreen
import org.mozilla.geckoview.GeckoSession
import org.mozilla.geckoview.GeckoView

class MainActivity : ComponentActivity() {

    private lateinit var runtimeHolder: GeckoRuntimeHolder
    private lateinit var environmentRepository: EnvironmentRepository
    private lateinit var syncController: SyncController
    private val sessions = mutableListOf<GeckoSession>()
    private var privateMode = false
    private var showControlCenter = false
    private var serverUrl = ""
    private var syncStatus = "not synchronized"
    private var environmentDocument: EnvironmentDocument? = null

    private val networkCallback = object : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) {
            environmentRepository.saveSession(sessions.mapNotNull { it.settings.toString() })
        }

        override fun onLost(network: Network) {
            environmentRepository.saveSession(sessions.mapNotNull { it.settings.toString() })
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        StorageLayout.ensure(this)
        runtimeHolder = GeckoRuntimeHolder(this)
        environmentRepository = EnvironmentRepository(this)
        syncController = SyncController(this)
        serverUrl = syncController.baseUrl()
        environmentDocument = environmentRepository.environmentDocument()
        restoreState(savedInstanceState)
        syncOnStart()
        registerNetworkCallback()
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    if (showControlCenter) {
                        ControlCenterScreen(document = environmentDocument(), statusLine = syncStatus, modifier = Modifier.fillMaxSize())
                    } else {
                        BrowserSurface()
                    }
                }
            }
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putBoolean(KEY_PRIVATE_MODE, privateMode)
        outState.putBoolean(KEY_CONTROL_CENTER, showControlCenter)
        outState.putStringArrayList(KEY_TAB_URLS, ArrayList(environmentRepository.pendingSessionTabs()))
        outState.putString(KEY_SERVER_URL, serverUrl)
        outState.putString(KEY_SYNC_STATUS, syncStatus)
    }

    override fun onDestroy() {
        unregisterNetworkCallback()
        super.onDestroy()
    }

    private fun restoreState(state: Bundle?) {
        privateMode = state?.getBoolean(KEY_PRIVATE_MODE) ?: false
        showControlCenter = state?.getBoolean(KEY_CONTROL_CENTER) ?: false
        serverUrl = state?.getString(KEY_SERVER_URL) ?: syncController.baseUrl()
        syncStatus = state?.getString(KEY_SYNC_STATUS) ?: "not synchronized"
        val pending = environmentRepository.pendingSessionTabs()
        if (pending.isEmpty()) {
            sessions.add(runtimeHolder.session(privateMode))
        } else {
            pending.forEach { _ -> sessions.add(runtimeHolder.session(privateMode)) }
        }
    }

    private fun registerNetworkCallback() {
        val manager = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        manager.registerDefaultNetworkCallback(networkCallback)
    }

    private fun unregisterNetworkCallback() {
        val manager = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        runCatching { manager.unregisterNetworkCallback(networkCallback) }
    }

    private fun environmentDocument(): EnvironmentDocument? = environmentDocument

    private fun syncOnStart() {
        Thread {
            val health = syncController.serverHealth()
            runOnUiThread {
                syncStatus = health.message
                requestSync()
            }
        }.start()
    }

    private fun requestSync() {
        Thread {
            val result: SyncResult = syncController.syncEnvironment(
                address = "https://example.com/",
                profileId = environmentDocument?.activeProfile ?: "default",
                resolverId = environmentDocument?.dns?.protocol ?: "system",
                privacyPreset = environmentDocument?.privacyPreset ?: "balanced",
                privateBrowsing = privateMode,
            )
            runOnUiThread {
                syncStatus = result.status + ": " + result.message
                result.document?.let { document -> environmentDocument = document }
                refreshContent()
            }
        }.start()
    }

    private fun exportDiagnostics() {
        Thread {
            val result = syncController.exportDiagnostics("redacted")
            runOnUiThread {
                syncStatus = result.status + ": " + result.message
            }
        }.start()
    }

    private fun refreshContent() {
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    if (showControlCenter) {
                        ControlCenterScreen(document = environmentDocument(), statusLine = syncStatus, modifier = Modifier.fillMaxSize())
                    } else {
                        BrowserSurface()
                    }
                }
            }
        }
    }

    @androidx.compose.runtime.Composable
    private fun BrowserSurface() {
        var address by remember { mutableStateOf("about:newtab") }
        Column(modifier = Modifier.fillMaxSize()) {
            Row(modifier = Modifier.fillMaxWidth().padding(8.dp)) {
                TextField(
                    value = address,
                    onValueChange = { value -> address = value },
                    label = { Text(stringResource(R.string.label_environment)) },
                    modifier = Modifier.weight(1f),
                )
                Button(onClick = { navigate(address) }) { Text(stringResource(R.string.action_reload)) }
                Button(onClick = { refreshSync() }) { Text(stringResource(R.string.action_sync)) }
                Button(onClick = { showControlCenter = true }) { Text(stringResource(R.string.label_diagnostics)) }
                Button(onClick = { exportDiagnostics() }) { Text(stringResource(R.string.action_export_redacted)) }
                Button(onClick = { togglePrivateMode() }) { Text(stringResource(R.string.action_private_mode)) }
            }
            AndroidView(
                modifier = Modifier.fillMaxSize(),
                factory = { context ->
                    GeckoView(context).apply {
                        setSession(sessions.first())
                    }
                },
            )
        }
    }

    private fun navigate(url: String) {
        sessions.first().loadUri(url)
    }

    private fun refreshSync() {
        syncStatus = "synchronizing with the application server"
        requestSync()
    }

    private fun togglePrivateMode() {
        privateMode = !privateMode
        sessions.clear()
        sessions.add(runtimeHolder.session(privateMode))
        refreshContent()
        refreshSync()
    }

    companion object {
        private const val KEY_PRIVATE_MODE = "private_mode"
        private const val KEY_CONTROL_CENTER = "control_center"
        private const val KEY_TAB_URLS = "tab_urls"
        private const val KEY_SERVER_URL = "server_url"
        private const val KEY_SYNC_STATUS = "sync_status"
    }
}
