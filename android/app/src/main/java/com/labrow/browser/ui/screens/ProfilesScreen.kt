package com.labrow.browser.ui.screens

import androidx.compose.foundation.clickable
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
fun ProfilesScreen(state: AppState, modifier: Modifier = Modifier) {
    val scope = rememberCoroutineScope()
    var identifier by remember { mutableStateOf("default") }

    Column(modifier = modifier.verticalScroll(rememberScrollState()).padding(12.dp)) {
        SectionHeader(
            kicker = "profiles",
            title = "Environment profiles",
            subtitle = "A profile is a versioned document. Validation and migration run on the server before a profile becomes active.",
        )
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonViolet) {
            NeonField(label = "Profile identifier", value = identifier, onValueChange = { identifier = it })
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                NeonButton(label = "Load") { scope.launch { state.loadProfileDraft(identifier) } }
                NeonButton(label = "Validate") { scope.launch { state.validateDraft() } }
                NeonButton(label = "Save", emphasized = true) { scope.launch { state.saveProfileDraft(identifier) } }
                NeonButton(label = "Delete") { scope.launch { state.deleteProfile(identifier) } }
            }
            Spacer(Modifier.height(10.dp))
            if (state.profiles.isEmpty()) {
                Text("Profile list not loaded yet. Refresh from the button below.", color = BrandColors.haze, fontSize = 12.sp)
            } else {
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    state.profiles.take(4).forEach { entry ->
                        Column(modifier = Modifier.clickable { identifier = entry }) {
                            StatusChip(label = "profile", value = entry, tone = if (entry == identifier) BrandColors.neonViolet else BrandColors.haze)
                        }
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
            NeonButton(label = "Refresh list") { scope.launch { state.loadProfiles() } }
        }

        Spacer(Modifier.height(12.dp))
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonCyan) {
            Text("Document", color = BrandColors.snow, fontSize = 15.sp)
            Spacer(Modifier.height(8.dp))
            NeonField(label = "profile json", value = state.profileDraft, minLines = 12, onValueChange = { state.profileDraft = it })
        }

        Spacer(Modifier.height(12.dp))
        NeonPanel(modifier = Modifier.fillMaxWidth(), accent = BrandColors.neonAmber) {
            Text("Validation report", color = BrandColors.snow, fontSize = 15.sp)
            Spacer(Modifier.height(8.dp))
            ValueRow("last validation", state.validationSummary.take(160))
            Spacer(Modifier.height(8.dp))
            Text(state.validationSummary.take(900), color = BrandColors.mist, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
        }
        Spacer(Modifier.height(20.dp))
    }
}
