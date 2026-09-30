package com.labrow.browser.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
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
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.labrow.browser.core.EnvironmentDocument
import com.labrow.browser.ui.AppState
import com.labrow.browser.ui.theme.BrandColors
import com.labrow.browser.ui.theme.NeonButton
import com.labrow.browser.ui.theme.NeonField
import com.labrow.browser.ui.theme.NeonPanel
import com.labrow.browser.ui.theme.RingGauge
import com.labrow.browser.ui.theme.SectionHeader
import com.labrow.browser.ui.theme.StatTile
import com.labrow.browser.ui.theme.StatusChip
import com.labrow.browser.ui.theme.ToggleRow
import com.labrow.browser.ui.theme.ValueRow
import kotlinx.coroutines.launch

@Composable
fun EnvironmentScreen(state: AppState, modifier: Modifier = Modifier) {
    val scope = rememberCoroutineScope()
    var address by remember { mutableStateOf("https://example.com/") }
    var profile by remember { mutableStateOf("default") }
    var resolver by remember { mutableStateOf("cloudflare-doh") }
    var privacy by remember { mutableStateOf("balanced") }
    var privateBrowsing by remember { mutableStateOf(false) }

    Column(modifier = modifier.verticalScroll(rememberScrollState()).padding(12.dp)) {
        SectionHeader(
            kicker = "environment",
            title = "Virtual environment",
            subtitle = "One deterministic pipeline resolves location, timezone, locale, resolver and policy for every navigation.",
        )
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonRed) {
            NeonField(label = "Address", value = address, onValueChange = { address = it })
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                NeonField(label = "Profile", value = profile, modifier = Modifier.width(150.dp), onValueChange = { profile = it })
                NeonField(label = "Resolver", value = resolver, modifier = Modifier.width(170.dp), onValueChange = { resolver = it })
            }
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                listOf("balanced", "strict", "development").forEach { preset ->
                    StatusChip(
                        label = "preset",
                        value = preset,
                        tone = if (preset == privacy) BrandColors.neonViolet else BrandColors.haze,
                    )
                }
            }
            Spacer(Modifier.height(6.dp))
            ToggleRow(
                label = "Private browsing",
                checked = privateBrowsing,
                caption = "Private sessions never keep history and keep cookies session scoped",
                onCheckedChange = { privateBrowsing = it },
            )
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                NeonButton(label = "Resolve environment", emphasized = true) {
                    scope.launch { state.resolve(address, profile, resolver, privacy, privateBrowsing) }
                }
                NeonButton(label = "Strict") { privacy = "strict" }
                NeonButton(label = "Balanced") { privacy = "balanced" }
            }
        }

        val document = state.environment
        if (document == null) {
            Spacer(Modifier.height(12.dp))
            NeonPanel(modifier = Modifier.fillMaxWidth()) {
                Text("No environment has been resolved yet on this device.", color = BrandColors.haze, fontSize = 13.sp)
            }
            return@Column
        }

        Spacer(Modifier.height(12.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
            RingGauge(progress = confidence(document), label = percent(confidence(document)))
            Column(modifier = Modifier.fillMaxWidth()) {
                StatusChip(label = "status", value = document.status, tone = toneFor(document.status))
                Spacer(Modifier.height(6.dp))
                StatusChip(label = "state", value = document.state, tone = BrandColors.neonViolet)
                Spacer(Modifier.height(6.dp))
                StatusChip(label = "profile", value = document.activeProfile, tone = BrandColors.neonCyan)
            }
        }

        Spacer(Modifier.height(12.dp))
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonCyan) {
            Text("Surfaces", color = BrandColors.snow, fontSize = 15.sp)
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatTile(label = "latitude", value = format(document.location?.coordinate?.latitude), accent = BrandColors.neonRed)
                StatTile(label = "longitude", value = format(document.location?.coordinate?.longitude), accent = BrandColors.neonViolet)
            }
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatTile(label = "radius", value = format(document.location?.radiusMeters) + " m", accent = BrandColors.neonCyan)
                StatTile(label = "accuracy", value = format(document.location?.coordinate?.accuracyMeters) + " m", accent = BrandColors.neonAmber)
            }
            Spacer(Modifier.height(10.dp))
            ValueRow("source", document.location?.source ?: "virtual")
            ValueRow("mode", document.location?.mode ?: "manual")
            ValueRow("seed", document.location?.seed?.toString() ?: "not seeded")
            ValueRow("signals", document.location?.signals?.joinToString(", ") ?: "none")
        }

        Spacer(Modifier.height(12.dp))
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonViolet) {
            Text("Timezone and locale", color = BrandColors.snow, fontSize = 15.sp)
            Spacer(Modifier.height(8.dp))
            ValueRow("time zone", document.timezone?.zone ?: "not resolved")
            ValueRow("offset minutes", (document.timezone?.offsetMinutes ?: 0).toString())
            ValueRow("daylight saving", (document.timezone?.daylightSavingActive ?: false).toString())
            ValueRow("browser locale", document.locale?.browserLocale ?: "not resolved")
            ValueRow("http preference", document.locale?.httpLanguagePreference ?: "not resolved")
            ValueRow("operating system locale", document.locale?.operatingSystemLocale ?: "not controlled")
        }

        Spacer(Modifier.height(12.dp))
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonCyan) {
            Text("Resolver and privacy", color = BrandColors.snow, fontSize = 15.sp)
            Spacer(Modifier.height(8.dp))
            ValueRow("resolver", document.dns?.resolverName ?: "browser default")
            ValueRow("protocol", document.dns?.protocol ?: "system")
            ValueRow("tls", document.dns?.tlsStatus ?: "not applicable")
            ValueRow("fallback", document.dns?.fallbackState ?: "never")
            ValueRow("system resolver unchanged", (document.dns?.systemResolverUnchanged ?: true).toString())
            ValueRow("privacy preset", document.privacyPreset)
            ValueRow("webrtc policy", document.webrtcPolicy)
            ValueRow("private browsing", document.privateBrowsing.toString())
        }

        Spacer(Modifier.height(12.dp))
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonAmber) {
            Text("Pipeline stages", color = BrandColors.snow, fontSize = 15.sp)
            Spacer(Modifier.height(8.dp))
            if (document.stages.isEmpty()) {
                Text("Pipeline detail is not available for this document.", color = BrandColors.haze, fontSize = 12.sp)
            } else {
                document.stages.forEach { stage ->
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(stage.name, color = BrandColors.mist, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                        StatusChip(label = "stage", value = stage.status, tone = toneFor(stage.status))
                    }
                }
            }
        }

        Spacer(Modifier.height(12.dp))
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = toneFor(document.status)) {
            Text("Consistency findings", color = BrandColors.snow, fontSize = 15.sp)
            Spacer(Modifier.height(8.dp))
            if (document.conflicts.isEmpty()) {
                Text("No mismatch was reported across the environment surfaces.", color = BrandColors.haze, fontSize = 12.sp)
            } else {
                document.conflicts.forEach { conflict ->
                    Column(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                        StatusChip(label = conflict.severity, value = conflict.identifier, tone = toneFor(conflict.severity))
                        Spacer(Modifier.height(4.dp))
                        Text(conflict.message, color = BrandColors.mist, fontSize = 12.sp)
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
            Text(document.notices.joinToString(" "), color = BrandColors.haze, fontSize = 11.sp)
        }
        Spacer(Modifier.height(20.dp))
    }
}

private fun confidence(document: EnvironmentDocument): Float = (document.location?.confidence ?: 0.5).toFloat().coerceIn(0f, 1f)

private fun percent(value: Float): String = ((value * 100).toInt()).toString() + "%"

private fun format(value: Double?): String = if (value == null) "not set" else String.format("%.4f", value)

private fun toneFor(status: String): androidx.compose.ui.graphics.Color = when (status.uppercase()) {
    "OK", "PASS", "COMPATIBLE", "CONSISTENT", "SUCCESS" -> BrandColors.ok
    "FAIL", "FAILED", "FAILURE", "INVALID", "NOT_SUPPORTED", "ERROR" -> BrandColors.fail
    else -> BrandColors.warn
}
