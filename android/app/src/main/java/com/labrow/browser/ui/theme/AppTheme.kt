package com.labrow.browser.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.material3.Typography
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

val LaBrowShapes = RoundedCornerShape(18.dp)
val LaBrowSmallShapes = RoundedCornerShape(12.dp)
val LaBrowPill = RoundedCornerShape(999.dp)

val LaBrowTypography = Typography(
    headlineSmall = TextStyle(fontFamily = FontFamily.SansSerif, fontWeight = FontWeight.Bold, fontSize = 22.sp, letterSpacing = 0.4.sp),
    titleMedium = TextStyle(fontFamily = FontFamily.SansSerif, fontWeight = FontWeight.SemiBold, fontSize = 16.sp, letterSpacing = 0.3.sp),
    bodyMedium = TextStyle(fontFamily = FontFamily.SansSerif, fontWeight = FontWeight.Normal, fontSize = 13.5.sp),
    labelSmall = TextStyle(fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Medium, fontSize = 11.sp, letterSpacing = 0.6.sp),
)

private val LaBrowColorScheme = darkColorScheme(
    primary = BrandColors.neonViolet,
    onPrimary = BrandColors.snow,
    secondary = BrandColors.neonCyan,
    onSecondary = BrandColors.void,
    tertiary = BrandColors.neonRed,
    background = BrandColors.obsidian,
    onBackground = BrandColors.snow,
    surface = BrandColors.graphite,
    onSurface = BrandColors.snow,
    surfaceVariant = BrandColors.slate,
    onSurfaceVariant = BrandColors.mist,
    error = BrandColors.fail,
    onError = BrandColors.snow,
    outline = Color(0x33FFFFFF),
)

@Composable
fun LaBrowTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = LaBrowColorScheme, typography = LaBrowTypography, content = content)
}
