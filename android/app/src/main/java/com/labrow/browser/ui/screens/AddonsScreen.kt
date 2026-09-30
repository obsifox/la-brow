package com.labrow.browser.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.labrow.browser.ui.AppState
import com.labrow.browser.ui.theme.BrandColors
import com.labrow.browser.ui.theme.BrandGradients
import com.labrow.browser.ui.theme.LaBrowSmallShapes
import com.labrow.browser.ui.theme.NeonButton
import com.labrow.browser.ui.theme.NeonField
import com.labrow.browser.ui.theme.NeonPanel
import com.labrow.browser.ui.theme.SectionHeader
import com.labrow.browser.ui.theme.StatTile
import com.labrow.browser.ui.theme.StatusChip
import com.labrow.browser.ui.theme.ToggleRow
import com.labrow.browser.ui.theme.ValueRow
import kotlinx.coroutines.launch

private val SAMPLE_THEME = """
{
  "manifest_version": 2,
  "name": "Neon Grid",
  "version": "1.2.0",
  "type": "theme",
  "theme": {
    "colors": {
      "frame": "#05060A",
      "toolbar": "#12142B",
      "tab_selected": ["#FF2D3F", "#A855F7"],
      "toolbar_text": "#F5F7FF",
      "popup": "#12142B",
      "popup_text": "#F5F7FF"
    },
    "images": { "theme_frame": "header.png" }
  }
}
""".trimIndent()

@Composable
fun AddonsScreen(state: AppState, modifier: Modifier = Modifier) {
    val scope = rememberCoroutineScope()
    var manifestText by remember { mutableStateOf(SAMPLE_THEME) }
    var acknowledged by remember { mutableStateOf(false) }

    Column(modifier = modifier.verticalScroll(rememberScrollState()).padding(12.dp)) {
        SectionHeader(
            kicker = "add-ons",
            title = "Desktop themes and add-ons",
            subtitle = "Desktop Firefox theme manifests are translated into the application gradient, and every add-on install states that parts may not display correctly.",
        )

        val theme = state.theme
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonViolet) {
            Text("Active theme", color = BrandColors.snow, fontSize = 15.sp)
            Spacer(Modifier.height(8.dp))
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(96.dp)
                    .clip(LaBrowSmallShapes)
                    .background(BrandGradients.forStops(com.labrow.browser.core.ThemeEngine.stopsFrom(theme)))
                    .border(1.dp, BrandColors.hairline, LaBrowSmallShapes),
            )
            Spacer(Modifier.height(8.dp))
            ValueRow("theme", theme?.name ?: "product default")
            ValueRow("source", theme?.source ?: "product-default")
            ValueRow("stops", theme?.stops?.joinToString(" ") ?: "built in palette")
            ValueRow("frame image", theme?.frameImage ?: "none")
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                NeonButton(label = "Reload theme") { scope.launch { state.refreshTheme() } }
                NeonButton(label = "Activate selected") {
                    val identifier = state.addons.firstOrNull { it.type == "theme" }?.id
                    if (identifier != null) {
                        scope.launch { state.activateTheme(identifier) }
                    }
                }
            }
        }

        Spacer(Modifier.height(12.dp))
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonCyan) {
            Text("Install a desktop manifest", color = BrandColors.snow, fontSize = 15.sp)
            Spacer(Modifier.height(8.dp))
            NeonField(label = "manifest.json", value = manifestText, minLines = 8, onValueChange = { manifestText = it })
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                NeonButton(label = "Inspect") { scope.launch { state.inspectManifest(manifestText) } }
                NeonButton(label = "Install", emphasized = true) {
                    scope.launch { state.installManifest(manifestText, acknowledged) }
                }
            }
            Spacer(Modifier.height(8.dp))
            ToggleRow(
                label = "I understand the compatibility notice",
                checked = acknowledged,
                caption = "Required before an installation is recorded",
                onCheckedChange = { acknowledged = it },
            )
        }

        val inspection = state.inspection
        if (inspection != null) {
            Spacer(Modifier.height(12.dp))
            NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonAmber) {
                Text("Compatibility report", color = BrandColors.snow, fontSize = 15.sp)
                Spacer(Modifier.height(8.dp))
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    com.labrow.browser.ui.theme.RingGauge(progress = inspection.report.score.toFloat(), label = ((inspection.report.score * 100).toInt()).toString() + "%")
                    Column {
                        StatusChip(label = "manifest", value = inspection.manifestName, tone = BrandColors.neonViolet)
                        Spacer(Modifier.height(6.dp))
                        StatusChip(
                            label = "level",
                            value = inspection.report.level,
                            tone = if (inspection.report.level == "COMPATIBLE") BrandColors.ok else BrandColors.warn,
                        )
                    }
                }
                Spacer(Modifier.height(10.dp))
                NeonNotice(inspection.report.notice)
                Spacer(Modifier.height(10.dp))
                inspection.report.sections.take(6).forEach { item ->
                    ValueRow(item.surface, item.level)
                }
                Spacer(Modifier.height(8.dp))
                inspection.report.findings.take(6).forEach { finding ->
                    Column(modifier = Modifier.padding(vertical = 3.dp)) {
                        Text(finding.code, color = BrandColors.warn, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                        Text(finding.message, color = BrandColors.mist, fontSize = 12.sp)
                    }
                }
            }
        }

        Spacer(Modifier.height(12.dp))
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonIndigo) {
            Text("Runtime matrix", color = BrandColors.snow, fontSize = 15.sp)
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatTile(label = "surfaces", value = state.matrix.size.toString(), accent = BrandColors.neonCyan)
                StatTile(label = "unsupported", value = state.matrix.count { it.level == "unsupported" }.toString(), accent = BrandColors.fail)
            }
            Spacer(Modifier.height(8.dp))
            NeonButton(label = "Load matrix") { scope.launch { state.loadMatrix() } }
            Spacer(Modifier.height(8.dp))
            state.matrix.take(12).forEach { item ->
                ValueRow(item.surface, item.level)
            }
        }

        Spacer(Modifier.height(12.dp))
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonRed) {
            Text("Recorded add-ons", color = BrandColors.snow, fontSize = 15.sp)
            Spacer(Modifier.height(8.dp))
            NeonButton(label = "Refresh registry") { scope.launch { state.loadAddons() } }
            Spacer(Modifier.height(8.dp))
            if (state.addons.isEmpty()) {
                Text("No add-on recorded yet.", color = BrandColors.haze, fontSize = 12.sp)
            } else {
                state.addons.forEach { addon ->
                    Column(modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                            StatusChip(label = addon.type, value = addon.name, tone = BrandColors.neonViolet)
                            StatusChip(
                                label = "level",
                                value = addon.compatibilityLevel,
                                tone = if (addon.compatibilityLevel == "COMPATIBLE") BrandColors.ok else BrandColors.warn,
                            )
                        }
                        Spacer(Modifier.height(4.dp))
                        ValueRow("identifier", addon.id)
                        ValueRow("signature", addon.signature)
                        ValueRow("notice acknowledged", addon.noticeAcknowledged.toString())
                        Spacer(Modifier.height(6.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            NeonButton(label = "Activate theme") { scope.launch { state.activateTheme(addon.id) } }
                            NeonButton(label = "Remove") { scope.launch { state.removeAddon(addon.id) } }
                        }
                    }
                }
            }
        }
        Spacer(Modifier.height(20.dp))
    }
}

@Composable
private fun NeonNotice(text: String) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(LaBrowSmallShapes)
            .background(androidx.compose.ui.graphics.Color(0xFF1B1707))
            .border(1.dp, BrandColors.warn.copy(alpha = 0.5f), LaBrowSmallShapes)
            .padding(12.dp),
    ) {
        Text(text, color = BrandColors.warn, fontSize = 12.sp)
    }
}
