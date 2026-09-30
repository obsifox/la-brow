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
import com.labrow.browser.ui.theme.ValueRow
import kotlinx.coroutines.launch

@Composable
fun NetworkScreen(state: AppState, modifier: Modifier = Modifier) {
    val scope = rememberCoroutineScope()
    var resolver by remember { mutableStateOf("cloudflare-doh") }
    var name by remember { mutableStateOf("example.com") }
    var recordType by remember { mutableStateOf("A") }

    Column(modifier = modifier.verticalScroll(rememberScrollState()).padding(12.dp)) {
        SectionHeader(
            kicker = "network",
            title = "Resolver and transport",
            subtitle = "Resolver selection stays inside the browser. The operating system resolver configuration is read and hashed, never written.",
        )
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonCyan) {
            NeonField(label = "Resolver", value = resolver, onValueChange = { resolver = it })
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                NeonField(label = "Query name", value = name, onValueChange = { name = it })
                NeonField(label = "Record type", value = recordType, modifier = Modifier.width(120.dp), onValueChange = { recordType = it })
            }
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                NeonButton(label = "Run probe", emphasized = true) { scope.launch { state.runProbe(resolver, name, recordType) } }
                NeonButton(label = "List resolvers") { scope.launch { state.loadResolvers() } }
            }
            Spacer(Modifier.height(10.dp))
            Text(state.probeSummary, color = BrandColors.mist, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
        }

        Spacer(Modifier.height(12.dp))
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonViolet) {
            Text("Declared profiles", color = BrandColors.snow, fontSize = 15.sp)
            Spacer(Modifier.height(8.dp))
            if (state.resolvers.isEmpty()) {
                Text("Resolver list not loaded yet.", color = BrandColors.haze, fontSize = 12.sp)
            } else {
                state.resolvers.forEach { identifier -> ValueRow(identifier, "available") }
            }
        }

        Spacer(Modifier.height(12.dp))
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.ok) {
            Text("Isolation guarantees", color = BrandColors.snow, fontSize = 15.sp)
            Spacer(Modifier.height(8.dp))
            StatusChip(label = "operating system dns", value = "not modified", tone = BrandColors.ok)
            Spacer(Modifier.height(8.dp))
            Text(
                "Resolution happens inside the browser scope. System wide changes are forbidden by the product policy and are reported as a finding if a transport attempts one.",
                color = BrandColors.haze,
                fontSize = 12.sp,
            )
        }
        Spacer(Modifier.height(20.dp))
    }
}
