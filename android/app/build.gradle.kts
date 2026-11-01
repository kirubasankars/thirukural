plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.kirubasankars.thirukural"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.kirubasankars.thirukural"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"
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

// The published deck is the app. Copy it into the asset folder at build time
// so the APK stays in step with docs/index.html.
val deck = rootProject.file("../docs/index.html")
val generatedAssets = layout.buildDirectory.dir("generated/assets")

val copyDeck = tasks.register<Copy>("copyDeck") {
    from(deck)
    into(generatedAssets)
    rename { "index.html" }
}

android.sourceSets.getByName("main").assets.srcDir(generatedAssets)

tasks.configureEach {
    if (name.startsWith("merge") && name.endsWith("Assets")) {
        dependsOn(copyDeck)
    }
}

dependencies {
    implementation("androidx.activity:activity-ktx:1.9.3")
    implementation("androidx.webkit:webkit:1.12.1")
}
