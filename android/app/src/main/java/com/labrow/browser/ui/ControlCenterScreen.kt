package com.labrow.browser.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.labrow.browser.R
import com.labrow.browser.core.EnvironmentDocument

@Composable
fun ControlCenterScreen(document: EnvironmentDocument?, statusLine: String = "", modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        SectionTitle(stringResource(R.string.label_environment))
        Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
            Column(modifier = Modifier.padding(12.dp)) {
                BodyText(stringResource(R.string.label_server) + ": " + statusLine)
            }
        }
        if (document == null) {
            BodyText(stringResource(R.string.error_profile_invalid))
            return@Column
        }
        Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
            Column(modifier = Modifier.padding(12.dp)) {
                BodyText("${stringResource(R.string.label_active_profile)}: ${document.activeProfile}")
                BodyText("state: ${document.state}")
                BodyText("status: ${document.status}")
            }
        }
        SectionTitle(stringResource(R.string.label_location))
        document.location?.let { location ->
            Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                Column(modifier = Modifier.padding(12.dp)) {
                    BodyText("${stringResource(R.string.label_source)}: ${location.source}")
                    BodyText("${stringResource(R.string.label_confidence)}: ${location.confidence}")
                    BodyText("mode: ${location.mode}")
                    BodyText("radius: ${location.radiusMeters} m")
                    location.coordinate?.let { coordinate ->
                        BodyText("latitude: ${coordinate.latitude}")
                        BodyText("longitude: ${coordinate.longitude}")
                    }
                    location.seed?.let { seed -> BodyText("randomization seed: $seed") }
                }
            }
        }
        SectionTitle(stringResource(R.string.label_timezone))
        document.timezone?.let { timezone ->
            Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                Column(modifier = Modifier.padding(12.dp)) {
                    BodyText("zone: ${timezone.zone}")
                    BodyText("offset minutes: ${timezone.offsetMinutes}")
                    BodyText("daylight saving active: ${timezone.daylightSavingActive}")
                    BodyText("controlled surfaces: ${timezone.controlledSurfaces.size}")
                    BodyText("uncontrolled surfaces: ${timezone.uncontrolledSurfaces.size}")
                }
            }
        }
        SectionTitle(stringResource(R.string.label_locale))
        document.locale?.let { locale ->
            Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                Column(modifier = Modifier.padding(12.dp)) {
                    BodyText("browser locale: ${locale.browserLocale}")
                    BodyText("language preference: ${locale.languagePreference}")
                    BodyText("http language preference: ${locale.httpLanguagePreference}")
                    BodyText("operating system locale: ${locale.operatingSystemLocale}")
                }
            }
        }
        SectionTitle(stringResource(R.string.label_dns))
        document.dns?.let { dns ->
            Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                Column(modifier = Modifier.padding(12.dp)) {
                    BodyText("resolver: ${dns.resolverName}")
                    BodyText("protocol: ${dns.protocol}")
                    BodyText("endpoint: ${dns.endpoint}")
                    BodyText("tls: ${dns.tlsStatus}")
                    BodyText("fallback: ${dns.fallbackState}")
                    BodyText("system resolver unchanged: ${dns.systemResolverUnchanged}")
                }
            }
        }
        SectionTitle(stringResource(R.string.label_webrtc))
        Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
            Column(modifier = Modifier.padding(12.dp)) {
                BodyText("webrtc policy: ${document.webrtcPolicy}")
                BodyText("privacy preset: ${document.privacyPreset}")
                BodyText("private browsing: ${if (document.privateBrowsing) "enabled" else "disabled"}")
            }
        }
        SectionTitle(stringResource(R.string.label_diagnostics))
        Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
            Column(modifier = Modifier.padding(12.dp)) {
                if (document.conflicts.isEmpty()) {
                    BodyText("no conflicts reported")
                } else {
                    document.conflicts.forEach { conflict ->
                        BodyText("${conflict.severity}: ${conflict.message}")
                    }
                }
            }
        }
        Card(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
            Column(modifier = Modifier.padding(12.dp)) {
                BodyText(stringResource(R.string.notice_no_anonymity_guarantee))
                BodyText(stringResource(R.string.notice_no_system_dns_change))
                BodyText(stringResource(R.string.notice_virtual_mode_no_fallback))
            }
        }
    }
}

@Composable
private fun SectionTitle(text: String) {
    Text(text = text, style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(top = 12.dp, bottom = 4.dp))
}

@Composable
private fun BodyText(text: String) {
    Text(text = text, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(vertical = 2.dp))
}
