package com.labrow.browser.core

data class EnvironmentCoordinate(
    val latitude: Double,
    val longitude: Double,
    val accuracyMeters: Double,
)

data class EnvironmentLocation(
    val mode: String,
    val source: String,
    val confidence: Double,
    val country: String?,
    val city: String?,
    val radiusMeters: Double,
    val coordinate: EnvironmentCoordinate?,
    val seed: Long?,
    val signals: List<String>,
)

data class EnvironmentTimezone(
    val zone: String,
    val offsetMinutes: Int,
    val daylightSavingActive: Boolean,
    val controlledSurfaces: List<String>,
    val uncontrolledSurfaces: List<String>,
)

data class EnvironmentLocale(
    val browserLocale: String,
    val languagePreference: String,
    val httpLanguagePreference: String,
    val operatingSystemLocale: String,
)

data class EnvironmentDns(
    val resolverName: String,
    val protocol: String,
    val endpoint: String,
    val tlsStatus: String,
    val fallbackState: String,
    val systemResolverUnchanged: Boolean,
)

data class EnvironmentStage(
    val name: String,
    val status: String,
    val detail: String,
)

data class EnvironmentConflict(
    val identifier: String,
    val severity: String,
    val message: String,
)

data class EnvironmentDocument(
    val schemaVersion: Int,
    val generatedAt: String,
    val status: String,
    val state: String,
    val activeProfile: String,
    val location: EnvironmentLocation?,
    val timezone: EnvironmentTimezone?,
    val locale: EnvironmentLocale?,
    val dns: EnvironmentDns?,
    val webrtcPolicy: String,
    val privacyPreset: String,
    val privateBrowsing: Boolean,
    val conflicts: List<EnvironmentConflict>,
    val stages: List<EnvironmentStage>,
    val invariantCount: Int,
    val geoState: String,
    val notices: List<String>,
)
