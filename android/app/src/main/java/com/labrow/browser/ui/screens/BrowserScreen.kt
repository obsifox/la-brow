package com.labrow.browser.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.labrow.browser.ui.theme.NeonButton
import com.labrow.browser.ui.theme.NeonField
import com.labrow.browser.ui.theme.NeonPanel
import com.labrow.browser.ui.theme.SectionHeader
import com.labrow.browser.ui.theme.StatusChip
import com.labrow.browser.ui.theme.BrandColors
import org.mozilla.geckoview.GeckoSession
import org.mozilla.geckoview.GeckoView

@Composable
fun BrowserScreen(
    session: GeckoSession?,
    homeAddress: String,
    modifier: Modifier = Modifier,
) {
    var address by remember { mutableStateOf(homeAddress) }
    var loading by remember { mutableStateOf(true) }

    Column(modifier = modifier.fillMaxSize().padding(12.dp)) {
        SectionHeader(
            kicker = "browser",
            title = "Session surface",
            subtitle = "GeckoView renders the page while the environment layer supplies location, timezone, locale and resolver state.",
        )
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonRed) {
            NeonField(label = "Address", value = address, onValueChange = { address = it })
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                NeonButton(label = "Go", emphasized = true) {
                    session?.loadUri(address)
                    loading = false
                }
                NeonButton(label = "Back") { session?.goBack() }
                NeonButton(label = "Forward") { session?.goForward() }
                NeonButton(label = "Reload") { session?.reload() }
            }
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatusChip(label = "engine", value = "geckoview 130", tone = BrandColors.neonCyan)
                StatusChip(label = "remote debugging", value = "disabled", tone = BrandColors.ok)
                StatusChip(label = "session", value = if (session == null) "starting" else "open", tone = BrandColors.neonViolet)
            }
        }
        Spacer(Modifier.height(12.dp))
        NeonPanel(modifier = Modifier.fillMaxWidth().height(520.dp), accent = BrandColors.neonViolet) {
            if (session == null) {
                androidx.compose.material3.Text("Engine session is starting.", color = BrandColors.haze)
            } else {
                AndroidView(
                    factory = { context ->
                        GeckoView(context).apply { setSession(session) }
                    },
                    modifier = Modifier.fillMaxSize(),
                )
            }
        }
    }
}
