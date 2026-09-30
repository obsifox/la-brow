package com.labrow.browser

import android.net.ConnectivityManager
import android.net.Network
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import com.labrow.browser.core.EnvironmentRepository
import com.labrow.browser.core.GeckoRuntimeHolder
import com.labrow.browser.ui.AppShell
import com.labrow.browser.ui.AppState
import com.labrow.browser.ui.theme.LaBrowTheme
import org.mozilla.geckoview.GeckoSession

class MainActivity : ComponentActivity() {

    private lateinit var runtimeHolder: GeckoRuntimeHolder
    private lateinit var environmentRepository: EnvironmentRepository
    private var sessionHandle: GeckoSession? = null
    private var privateMode = false

    private val networkCallback = object : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) {
            environmentRepository.saveSession(listOf("network-available"))
        }

        override fun onLost(network: Network) {
            environmentRepository.saveSession(listOf("network-lost"))
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        runtimeHolder = GeckoRuntimeHolder(applicationContext)
        environmentRepository = EnvironmentRepository(applicationContext)
        registerNetworkCallback()
        setContent {
            val state = remember { AppState(applicationContext) }
            var session by remember { mutableStateOf<GeckoSession?>(sessionHandle) }
            LaunchedEffect(Unit) {
                session = ensureSession()
                state.refreshHealth()
                state.loadProfiles()
                state.loadResolvers()
                state.refreshTheme()
                state.loadAddons()
                state.loadMatrix()
            }
            LaBrowTheme {
                AppShell(state = state, session = session)
            }
        }
    }

    private fun ensureSession(): GeckoSession {
        val current = sessionHandle
        if (current != null) {
            return current
        }
        val created = runtimeHolder.session(privateMode)
        sessionHandle = created
        return created
    }

    private fun registerNetworkCallback() {
        val manager = getSystemService(ConnectivityManager::class.java)
        manager?.registerDefaultNetworkCallback(networkCallback)
    }

    override fun onDestroy() {
        val manager = getSystemService(ConnectivityManager::class.java)
        manager?.unregisterNetworkCallback(networkCallback)
        sessionHandle?.close()
        sessionHandle = null
        super.onDestroy()
    }
}
