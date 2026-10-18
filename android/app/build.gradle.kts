plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.greggaynor.tibetan"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.greggaynor.tibetan"
        minSdk = 26
        targetSdk = 34
        // Bump on every build worth installing; it shows in Settings → Apps → Tibetan.
        versionCode = 1
        versionName = "1 — first"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

// No libraries: the shell is a WebView and the Storage Access Framework, both in the platform.
