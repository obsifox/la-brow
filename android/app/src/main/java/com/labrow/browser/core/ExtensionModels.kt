package com.labrow.browser.core

data class CompatibilityFinding(
    val code: String,
    val severity: String,
    val message: String,
    val detail: String,
)

data class CompatibilityItem(
    val surface: String,
    val level: String,
    val note: String,
)

data class CompatibilityReport(
    val level: String,
    val score: Double,
    val sections: List<CompatibilityItem>,
    val permissions: List<CompatibilityItem>,
    val findings: List<CompatibilityFinding>,
    val notice: String,
    val runtimeEngine: String,
)

data class GameTheme(
    val id: String,
    val name: String,
    val source: String,
    val compositionLevel: String,
    val stops: List<String>,
    val accent: String,
    val accentGlow: String,
    val palette: Map<String, String>,
    val findings: List<CompatibilityFinding>,
    val frameImage: String?,
)

data class InstalledAddon(
    val id: String,
    val name: String,
    val version: String,
    val type: String,
    val compatibilityLevel: String,
    val compatibilityScore: Double,
    val signature: String,
    val noticeAcknowledged: Boolean,
    val installedAt: String,
)

data class AddonInspection(
    val manifestName: String,
    val manifestType: String,
    val report: CompatibilityReport,
    val theme: GameTheme?,
    val previewCode: String,
)
