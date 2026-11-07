
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

android {
    namespace = "id.manajemen.mikrotik"
    compileSdk = 35

    defaultConfig {
        applicationId = "id.manajemen.mikrotik"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }
}

chaquopy {
    defaultConfig {
        version = "3.13"
        pip {
            install("Flask==3.1.3")
            install("RouterOS-api==0.21.0")
        }
    }
}
