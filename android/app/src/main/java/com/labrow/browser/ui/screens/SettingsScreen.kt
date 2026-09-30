package com.labrow.browser.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.labrow.browser.ui.AppState
import com.labrow.browser.ui.theme.BrandColors
import com.labrow.browser.ui.theme.NeonButton
import com.labrow.browser.ui.theme.NeonField
import com.labrow.browser.ui.theme.NeonPanel
import com.labrow.browser.ui.theme.SectionHeader
import com.labrow.browser.ui.theme.StatusChip
import com.labrow.browser.ui.theme.ToggleRow
import com.labrow.browser.ui.theme.ValueRow
import kotlinx.coroutines.launch

@Composable
fun SettingsScreen(state: AppState, modifier: Modifier = Modifier) {
    val scope = rememberCoroutineScope()
    var server by remember { mutableStateOf(state.serverUrl) }
    var defaultAddress by remember { mutableStateOf("https://example.com/") }
    var level by remember { mutableStateOf("redacted") }
    var privateDefault by remember { mutableStateOf(false) }

    Column(modifier = modifier.verticalScroll(rememberScrollState()).padding(12.dp)) {
        SectionHeader(
            kicker = "settings",
            title = "Application server",
            subtitle = "The mobile application asks the server for every environment decision, so the desktop and mobile control centers observe the same values.",
        )
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonViolet) {
            NeonField(label = "Server base address", value = server, onValueChange = { server = it })
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                NeonButton(label = "Apply address", emphasized = true) {
                    state.updateServer(server)
                    scope.launch { state.refreshHealth() }
                }
                NeonButton(label = "Check health") { scope.launch { state.refreshHealth() } }
            }
            Spacer(Modifier.height(10.dp))
            ValueRow("server", state.serverUrl)
            ValueRow("health", state.healthLine)
            ValueRow("status", state.statusLine)
        }

        Spacer(Modifier.height(12.dp))
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonCyan) {
            Text("Server side defaults", color = BrandColors.snow, fontSize = 15.sp)
            Spacer(Modifier.height(8.dp))
            NeonField(label = "Default address", value = defaultAddress, onValueChange = { defaultAddress = it })
            Spacer(Modifier.height(8.dp))
            NeonField(label = "Diagnostics level", value = level, onValueChange = { level = it })
            Spacer(Modifier.height(6.dp))
            ToggleRow(
                label = "Private browsing by default",
                checked = privateDefault,
                caption = "Applied to new sessions requested from this device",
                onCheckedChange = { privateDefault = it },
            )
            Spacer(Modifier.height(8.dp))
            NeonButton(label = "Save on server", emphasized = true) {
                scope.launch { state.saveServerSettings(defaultAddress, "balanced", level, privateDefault) }
            }
        }

        Spacer(Modifier.height(12.dp))
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonAmber) {
            Text("Diagnostics", color = BrandColors.snow, fontSize = 15.sp)
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                NeonButton(label = "Generate report") { scope.launch { state.loadDiagnostics(level) } }
                NeonButton(label = "Policy scan state") { scope.launch { state.loadScans() } }
            }
            Spacer(Modifier.height(10.dp))
            Text(state.diagnostics.take(1200), color = BrandColors.mist, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
        }

        Spacer(Modifier.height(12.dp))
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.ok) {
            Text("Product statements", color = BrandColors.snow, fontSize = 15.sp)
            Spacer(Modifier.height(8.dp))
            StatusChip(label = "anonymity", value = "not guaranteed", tone = BrandColors.warn)
            Spacer(Modifier.height(8.dp))
            Text(
                "Environment controls do not guarantee anonymity and do not change the public address observed by websites. Virtual location mode never falls back to the device location provider.",
                color = BrandColors.haze,
                fontSize = 12.sp,
            )
        }
        Spacer(Modifier.height(20.dp))
    }
}
