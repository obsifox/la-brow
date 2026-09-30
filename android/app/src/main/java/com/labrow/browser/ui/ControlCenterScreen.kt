package com.labrow.browser.ui

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
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.labrow.browser.core.EnvironmentDocument
import com.labrow.browser.ui.theme.BrandColors
import com.labrow.browser.ui.theme.NeonPanel
import com.labrow.browser.ui.theme.SectionHeader
import com.labrow.browser.ui.theme.StatTile
import com.labrow.browser.ui.theme.StatusChip
import com.labrow.browser.ui.theme.ValueRow

@Composable
fun ControlCenterScreen(document: EnvironmentDocument?, statusLine: String = "", modifier: Modifier = Modifier) {
    Column(modifier = modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(14.dp)) {
        SectionHeader(
            kicker = "control center",
            title = "Environment summary",
            subtitle = "Compact view of the resolved environment for the current session.",
        )
        NeonPanel(modifier = Modifier.fillMaxWidth()) {
            ValueRow("server status", if (statusLine.isEmpty()) "not synchronized" else statusLine)
            if (document == null) {
                Spacer(Modifier.height(6.dp))
                Text("No environment document is stored on this device yet.", color = BrandColors.haze, fontSize = 12.sp)
                return@NeonPanel
            }
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatusChip(label = "status", value = document.status, tone = BrandColors.ok)
                StatusChip(label = "state", value = document.state, tone = BrandColors.neonViolet)
            }
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatTile(label = "latitude", value = document.location?.coordinate?.latitude?.toString() ?: "not set", accent = BrandColors.neonRed)
                StatTile(label = "longitude", value = document.location?.coordinate?.longitude?.toString() ?: "not set", accent = BrandColors.neonCyan)
            }
            Spacer(Modifier.height(10.dp))
            ValueRow("time zone", document.timezone?.zone ?: "not resolved")
            ValueRow("browser locale", document.locale?.browserLocale ?: "not resolved")
            ValueRow("resolver", document.dns?.resolverName ?: "browser default")
            ValueRow("privacy preset", document.privacyPreset)
            ValueRow("webrtc policy", document.webrtcPolicy)
            ValueRow("private browsing", document.privateBrowsing.toString())
        }
    }
}
