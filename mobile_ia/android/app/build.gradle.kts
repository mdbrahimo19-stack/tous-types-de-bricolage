import java.util.Properties

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// Notifications push : le fichier Firebase (google-services.json) n'est pas dans Git (dépôt public).
// En CI il est recréé depuis le secret GOOGLE_SERVICES_JSON ; sans lui, l'app marche sans notifications.
if (file("google-services.json").exists()) {
    apply(plugin = "com.google.gms.google-services")
}

// Clé de signature fixe : android/key.properties (ignoré par Git).
// En CI, ce fichier est recréé à partir des secrets GitHub (voir .github/workflows/mobile.yml).
// Sans lui, l'APK est signé avec la clé de test (différente à chaque machine).
val keystorePropertiesFile = rootProject.file("key.properties")
val keystoreProperties = Properties().apply {
    if (keystorePropertiesFile.exists()) keystorePropertiesFile.inputStream().use { load(it) }
}

android {
    namespace = "dz.ttb.ttb_mobile"
    // flutter_local_notifications exige au moins le SDK 37
    compileSdk = maxOf(flutter.compileSdkVersion, 37)
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
        // exigé par flutter_local_notifications (notifications avec sonnerie)
        isCoreLibraryDesugaringEnabled = true
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "dz.ttb.ttb_mobile"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        // Uses the version code from pubspec.yaml. When using split APKs, 1000 * ABI_VERSION
        // is added automatically by Flutter. (https://developer.android.com/studio/build/configure-apk-splits#configure-APK-versions)
        // You can force using the value of versionCode by specifying the `-P force-version-code-ignoring-abi=true`
        // flag during build.
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    // Deux applications installables côte à côte (flutter build apk --flavor client|pro).
    // « client » garde l'identifiant historique : la mise à jour s'installe par-dessus l'ancienne app.
    flavorDimensions += "app"
    productFlavors {
        create("client") {
            dimension = "app"
            manifestPlaceholders["appLabel"] = "BRICOOL"
        }
        create("pro") {
            dimension = "app"
            applicationIdSuffix = ".pro"
            manifestPlaceholders["appLabel"] = "BRICOOL Pro"
        }
    }

    signingConfigs {
        if (keystorePropertiesFile.exists()) {
            create("release") {
                keyAlias = keystoreProperties.getProperty("keyAlias")
                keyPassword = keystoreProperties.getProperty("keyPassword")
                storeFile = file(keystoreProperties.getProperty("storeFile"))
                storePassword = keystoreProperties.getProperty("storePassword")
            }
        }
    }

    buildTypes {
        release {
            // Même clé à chaque compilation : l'APK s'installe par-dessus la version précédente.
            signingConfig = if (keystorePropertiesFile.exists()) {
                signingConfigs.getByName("release")
            } else {
                signingConfigs.getByName("debug")
            }
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}

dependencies {
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")
}
