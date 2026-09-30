package com.labrow.browser.ui.theme

import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

object BrandGradients {
    fun backdrop(): Brush = Brush.linearGradient(
        colors = listOf(
            BrandColors.void,
            BrandColors.midnight,
            Color(0xFF1B0B2E),
            BrandColors.obsidian,
        ),
        start = Offset.Zero,
        end = Offset.Infinite,
    )

    fun pane(): Brush = Brush.linearGradient(
        colors = listOf(
            Color(0xEE151A22),
            Color(0xEE0E1016),
        ),
        start = Offset.Zero,
        end = Offset.Infinite,
    )

    fun primary(): Brush = Brush.linearGradient(
        colors = listOf(BrandColors.neonRed, BrandColors.neonViolet),
        start = Offset.Zero,
        end = Offset.Infinite,
    )

    fun secondary(): Brush = Brush.linearGradient(
        colors = listOf(BrandColors.neonCyan, BrandColors.neonIndigo),
        start = Offset.Zero,
        end = Offset.Infinite,
    )

    fun frame(): Brush = Brush.linearGradient(
        colors = listOf(
            Color(0x66FF2D3F),
            Color(0x66A855F7),
            Color(0x3322D3EE),
        ),
        start = Offset.Zero,
        end = Offset.Infinite,
    )

    fun rail(): Brush = Brush.verticalGradient(
        colors = listOf(BrandColors.neonRed.copy(alpha = 0.9f), BrandColors.neonViolet.copy(alpha = 0.25f)),
    )

    fun forStops(stops: List<Color>): Brush {
        if (stops.size < 2) {
            return primary()
        }
        return Brush.linearGradient(colors = stops, start = Offset.Zero, end = Offset.Infinite)
    }

    fun glow(color: Color): Brush = Brush.radialGradient(
        colors = listOf(color.copy(alpha = 0.35f), Color.Transparent),
    )
}
