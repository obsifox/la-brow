package com.labrow.browser.ui.theme

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun GradientBackdrop(modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    val transition = rememberInfiniteTransition(label = "backdrop")
    val drift = transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(animation = tween(14000, easing = LinearEasing), repeatMode = RepeatMode.Reverse),
        label = "drift",
    )
    Box(modifier = modifier.fillMaxSize().background(BrandGradients.backdrop())) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val radius = size.minDimension * 0.7f
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(BrandColors.neonViolet.copy(alpha = 0.22f), Color.Transparent),
                    center = Offset(size.width * (0.2f + 0.6f * drift.value), size.height * 0.12f),
                    radius = radius,
                ),
                radius = radius,
                center = Offset(size.width * (0.2f + 0.6f * drift.value), size.height * 0.12f),
            )
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(BrandColors.neonRed.copy(alpha = 0.18f), Color.Transparent),
                    center = Offset(size.width * (0.85f - 0.5f * drift.value), size.height * 0.85f),
                    radius = radius * 0.9f,
                ),
                radius = radius * 0.9f,
                center = Offset(size.width * (0.85f - 0.5f * drift.value), size.height * 0.85f),
            )
            val step = 44f
            var x = 0f
            while (x < size.width) {
                drawLine(Color(0x0AFFFFFF), Offset(x, 0f), Offset(x, size.height), strokeWidth = 1f)
                x += step
            }
            var y = 0f
            while (y < size.height) {
                drawLine(Color(0x0AFFFFFF), Offset(0f, y), Offset(size.width, y), strokeWidth = 1f)
                y += step
            }
        }
        content()
    }
}

@Composable
fun NeonPanel(
    modifier: Modifier = Modifier,
    accent: Color = BrandColors.neonViolet,
    content: @Composable () -> Unit,
) {
    Box(
        modifier = modifier
            .clip(LaBrowShapes)
            .background(BrandGradients.pane())
            .border(width = 1.dp, brush = Brush.linearGradient(listOf(accent.copy(alpha = 0.55f), Color(0x1AFFFFFF))), shape = LaBrowShapes)
            .padding(16.dp),
    ) {
        Column { content() }
    }
}

@Composable
fun SectionHeader(kicker: String, title: String, subtitle: String? = null) {
    Column(modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp)) {
        Text(kicker.uppercase(), color = BrandColors.neonCyan, fontSize = 10.sp, fontFamily = FontFamily.Monospace, letterSpacing = 2.sp)
        Spacer(Modifier.height(4.dp))
        Text(title, color = BrandColors.snow, fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(6.dp))
        Box(Modifier.width(96.dp).height(3.dp).clip(LaBrowPill).background(BrandGradients.primary()))
        if (subtitle != null) {
            Spacer(Modifier.height(8.dp))
            Text(subtitle, color = BrandColors.haze, fontSize = 12.sp)
        }
    }
}

@Composable
fun NeonButton(
    label: String,
    modifier: Modifier = Modifier,
    emphasized: Boolean = false,
    enabled: Boolean = true,
    onClick: () -> Unit,
) {
    val brush = if (emphasized) BrandGradients.primary() else BrandGradients.pane()
    val border = if (enabled) 1.dp else 0.dp
    Box(
        modifier = modifier
            .clip(LaBrowSmallShapes)
            .background(brush)
            .border(border, BrandColors.hairline, LaBrowSmallShapes)
            .clickable(enabled = enabled) { onClick() }
            .padding(horizontal = 16.dp, vertical = 10.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            label,
            color = if (enabled) BrandColors.snow else BrandColors.haze,
            fontSize = 13.sp,
            fontWeight = FontWeight.SemiBold,
        )
    }
}

@Composable
fun StatusChip(label: String, value: String, tone: Color = BrandColors.neonCyan) {
    Row(
        modifier = Modifier
            .clip(LaBrowPill)
            .background(Color(0x1AFFFFFF))
            .border(1.dp, tone.copy(alpha = 0.45f), LaBrowPill)
            .padding(horizontal = 12.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(Modifier.size(7.dp).clip(LaBrowPill).background(tone))
        Spacer(Modifier.width(8.dp))
        Text(label.uppercase(), color = BrandColors.haze, fontSize = 9.sp, fontFamily = FontFamily.Monospace, letterSpacing = 1.sp)
        Spacer(Modifier.width(6.dp))
        Text(value, color = BrandColors.snow, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
fun StatTile(label: String, value: String, caption: String? = null, accent: Color = BrandColors.neonViolet) {
    Column(
        modifier = Modifier
            .clip(LaBrowSmallShapes)
            .background(Color(0x14141414))
            .border(1.dp, accent.copy(alpha = 0.3f), LaBrowSmallShapes)
            .padding(12.dp),
    ) {
        Text(label.uppercase(), color = accent, fontSize = 9.sp, fontFamily = FontFamily.Monospace, letterSpacing = 1.2.sp)
        Spacer(Modifier.height(6.dp))
        Text(value, color = BrandColors.snow, fontSize = 18.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
        if (caption != null) {
            Spacer(Modifier.height(4.dp))
            Text(caption, color = BrandColors.haze, fontSize = 11.sp)
        }
    }
}

@Composable
fun ValueRow(label: String, value: String, accent: Color = BrandColors.neonCyan) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 5.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(label, color = BrandColors.haze, fontSize = 12.sp)
        Text(value, color = accent, fontSize = 12.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Medium)
    }
}

@Composable
fun NeonField(
    label: String,
    value: String,
    modifier: Modifier = Modifier,
    minLines: Int = 1,
    onValueChange: (String) -> Unit,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label, fontSize = 11.sp) },
        modifier = modifier.fillMaxWidth(),
        minLines = minLines,
        shape = LaBrowSmallShapes,
        textStyle = androidx.compose.ui.text.TextStyle(fontSize = 12.5.sp, color = BrandColors.snow, fontFamily = FontFamily.Monospace),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = BrandColors.neonViolet,
            unfocusedBorderColor = BrandColors.hairline,
            focusedContainerColor = Color(0x66101014),
            unfocusedContainerColor = Color(0x44101014),
            cursorColor = BrandColors.neonCyan,
            focusedLabelColor = BrandColors.neonCyan,
            unfocusedLabelColor = BrandColors.haze,
        ),
    )
}

@Composable
fun ToggleRow(label: String, checked: Boolean, caption: String? = null, onCheckedChange: (Boolean) -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.fillMaxWidth(0.75f)) {
            Text(label, color = BrandColors.snow, fontSize = 13.sp)
            if (caption != null) {
                Text(caption, color = BrandColors.haze, fontSize = 11.sp)
            }
        }
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            colors = SwitchDefaults.colors(
                checkedThumbColor = BrandColors.snow,
                checkedTrackColor = BrandColors.neonViolet,
                uncheckedThumbColor = BrandColors.haze,
                uncheckedTrackColor = BrandColors.steel,
            ),
        )
    }
}

@Composable
fun NeonMeter(progress: Float, accent: Color = BrandColors.neonViolet, modifier: Modifier = Modifier) {
    val clamped = progress.coerceIn(0f, 1f)
    Box(modifier = modifier.fillMaxWidth().height(8.dp).clip(LaBrowPill).background(Color(0x33FFFFFF))) {
        Box(
            modifier = Modifier
                .fillMaxWidth(clamped)
                .height(8.dp)
                .clip(LaBrowPill)
                .background(Brush.horizontalGradient(listOf(accent, BrandColors.neonCyan))),
        )
    }
}

@Composable
fun RingGauge(progress: Float, label: String, accent: Color = BrandColors.neonCyan) {
    Box(modifier = Modifier.size(96.dp), contentAlignment = Alignment.Center) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val stroke = 8f
            drawArc(
                color = Color(0x22FFFFFF),
                startAngle = 135f,
                sweepAngle = 270f,
                useCenter = false,
                style = Stroke(width = stroke, cap = StrokeCap.Round),
                size = Size(size.width - stroke, size.height - stroke),
                topLeft = Offset(stroke / 2f, stroke / 2f),
            )
            drawArc(
                brush = Brush.sweepGradient(listOf(accent, BrandColors.neonViolet, accent)),
                startAngle = 135f,
                sweepAngle = 270f * progress.coerceIn(0f, 1f),
                useCenter = false,
                style = Stroke(width = stroke, cap = StrokeCap.Round),
                size = Size(size.width - stroke, size.height - stroke),
                topLeft = Offset(stroke / 2f, stroke / 2f),
            )
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(label, color = BrandColors.snow, fontSize = 16.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
            Text("score", color = BrandColors.haze, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
        }
    }
}
