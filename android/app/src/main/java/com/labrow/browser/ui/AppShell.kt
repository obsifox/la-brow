package com.labrow.browser.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.labrow.browser.core.ThemeEngine
import com.labrow.browser.ui.screens.AddonsScreen
import com.labrow.browser.ui.screens.BrowserScreen
import com.labrow.browser.ui.screens.EnvironmentScreen
import com.labrow.browser.ui.screens.NetworkScreen
import com.labrow.browser.ui.screens.ProfilesScreen
import com.labrow.browser.ui.screens.SettingsScreen
import com.labrow.browser.ui.theme.BrandColors
import com.labrow.browser.ui.theme.BrandGradients
import com.labrow.browser.ui.theme.GradientBackdrop
import com.labrow.browser.ui.theme.LaBrowPill
import com.labrow.browser.ui.theme.LaBrowSmallShapes
import com.labrow.browser.ui.theme.NeonMeter
import org.mozilla.geckoview.GeckoSession

enum class Destination(val label: String) {
    Browser("Browser"),
    Environment("Environment"),
    Addons("Add-ons"),
    Network("Network"),
    Profiles("Profiles"),
    Settings("Settings"),
}

@Composable
fun AppShell(state: AppState, session: GeckoSession?, modifier: Modifier = Modifier) {
    var destination by remember { mutableStateOf(Destination.Environment) }
    val stops = ThemeEngine.stopsFrom(state.theme)
    val accentBrush = if (stops.size >= 2) BrandGradients.forStops(stops) else BrandGradients.primary()

    GradientBackdrop(modifier = modifier) {
        Column(modifier = Modifier.fillMaxSize()) {
            TopHud(state = state, brush = accentBrush)
            Box(modifier = Modifier.fillMaxWidth().weight(1f)) {
                when (destination) {
                    Destination.Browser -> BrowserScreen(session = session, homeAddress = "https://example.com/")
                    Destination.Environment -> EnvironmentScreen(state = state)
                    Destination.Addons -> AddonsScreen(state = state)
                    Destination.Network -> NetworkScreen(state = state)
                    Destination.Profiles -> ProfilesScreen(state = state)
                    Destination.Settings -> SettingsScreen(state = state)
                }
            }
            ErrorBanner(message = state.lastError)
            BottomRail(destination = destination, brush = accentBrush, onSelect = { destination = it })
        }
    }
}

@Composable
private fun TopHud(state: AppState, brush: Brush) {
    val transition = rememberInfiniteTransition(label = "hud")
    val pulse by transition.animateFloat(
        initialValue = 0.6f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(animation = tween(2200, easing = LinearEasing), repeatMode = RepeatMode.Reverse),
        label = "pulse",
    )
    Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 12.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(38.dp)
                    .rotate(45f)
                    .clip(LaBrowSmallShapes)
                    .background(brush)
                    .border(1.dp, BrandColors.hairline, LaBrowSmallShapes),
            )
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text("LA BROW", color = BrandColors.snow, fontSize = 17.sp, fontWeight = FontWeight.Bold, letterSpacing = 2.sp)
                Text(state.healthLine, color = BrandColors.haze, fontSize = 10.5.sp, maxLines = 1)
            }
            Box(
                modifier = Modifier
                    .size(12.dp)
                    .clip(LaBrowPill)
                    .background(BrandColors.neonRed.copy(alpha = pulse)),
            )
        }
        Spacer(Modifier.height(10.dp))
        NeonMeter(progress = if (state.busy) 0.65f else 0.28f, accent = BrandColors.neonCyan)
        Spacer(Modifier.height(6.dp))
        Text(state.statusLine.uppercase(), color = BrandColors.haze, fontSize = 9.sp, fontFamily = FontFamily.Monospace, letterSpacing = 1.5.sp)
    }
}

@Composable
private fun ErrorBanner(message: String) {
    AnimatedVisibility(visible = message.isNotEmpty()) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 14.dp, vertical = 6.dp)
                .clip(LaBrowSmallShapes)
                .background(BrandColors.fail.copy(alpha = 0.16f))
                .border(1.dp, BrandColors.fail.copy(alpha = 0.45f), LaBrowSmallShapes)
                .padding(10.dp),
        ) {
            Text(message, color = BrandColors.fail, fontSize = 11.5.sp)
        }
    }
}

@Composable
private fun BottomRail(destination: Destination, brush: Brush, onSelect: (Destination) -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState())
            .padding(horizontal = 10.dp, vertical = 12.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Destination.entries.forEach { entry ->
            val selected = entry == destination
            Box(
                modifier = Modifier
                    .clip(LaBrowPill)
                    .background(if (selected) brush else BrandGradients.pane())
                    .border(1.dp, if (selected) BrandColors.hairline else BrandColors.hairline, LaBrowPill)
                    .clickable { onSelect(entry) }
                    .padding(horizontal = 14.dp, vertical = 9.dp),
            ) {
                Text(
                    entry.label.uppercase(),
                    color = if (selected) BrandColors.snow else BrandColors.haze,
                    fontSize = 10.sp,
                    fontFamily = FontFamily.Monospace,
                    letterSpacing = 1.sp,
                    fontWeight = if (selected) FontWeight.Bold else FontWeight.Normal,
                )
            }
        }
    }
}
