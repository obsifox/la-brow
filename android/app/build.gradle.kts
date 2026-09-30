plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

val releaseKeystoreFile = System.getenv("LABROW_KEYSTORE_FILE")
val releaseKeystorePassword = System.getenv("LABROW_KEYSTORE_PASSWORD")
val releaseKeyAlias = System.getenv("LABROW_KEY_ALIAS")
val releaseKeyPassword = System.getenv("LABROW_KEY_PASSWORD")
val releaseVersionName = System.getenv("LABROW_VERSION_NAME") ?: "0.2.0"
val releaseVersionCode = (System.getenv("LABROW_VERSION_CODE") ?: "1").toInt()

android {
    namespace = "com.labrow.browser"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.labrow.browser"
        minSdk = 26
        targetSdk = 36
        versionCode = releaseVersionCode
        versionName = releaseVersionName
    }

    signingConfigs {
        if (releaseKeystoreFile != null && releaseKeystorePassword != null && releaseKeyAlias != null && releaseKeyPassword != null) {
            create("release") {
                storeFile = file(releaseKeystoreFile)
                storePassword = releaseKeystorePassword
                keyAlias = releaseKeyAlias
                keyPassword = releaseKeyPassword
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = signingConfigs.findByName("release")
        }
    }

    packaging {
        jniLibs {
            useLegacyPackaging = true
        }
    }

    splits {
        abi {
            isEnable = true
            reset()
            include("arm64-v8a", "armeabi-v7a", "x86_64")
            isUniversalApk = true
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlin {
        compilerOptions {
            jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
        }
    }

    buildFeatures {
        compose = true
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation(platform("androidx.compose:compose-bom:2026.06.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-core")
    implementation("androidx.compose.animation:animation")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("org.mozilla.geckoview:geckoview:153.0.20260810162159")
    debugImplementation("androidx.compose.ui:ui-tooling")
    testImplementation("junit:junit:4.13.2")
}
