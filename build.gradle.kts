plugins {
    id("org.jetbrains.kotlin.jvm") version "2.2.0"
    id("org.jetbrains.intellij.platform") version "2.11.0"
}

group = "com.sqlscope"
version = "1.0.0"

// Target JVM 21 for both Kotlin and Java so they stay consistent.
// The installed JDK (25) will compile to this target without needing a toolchain download.
kotlin {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_21)
    }
}

java {
    sourceCompatibility = JavaVersion.VERSION_21
    targetCompatibility = JavaVersion.VERSION_21
}

repositories {
    mavenCentral()
    intellijPlatform {
        defaultRepositories()
    }
}

dependencies {
    intellijPlatform {
        // Target PhpStorm 2025.3 (build 253.x) — the instrumentation artifacts for
        // older builds (241.x / 2024.1) are not available in the JetBrains repo.
        // Change "PS" to "IU" for IntelliJ Ultimate or "DG" for DataGrip.
        phpstorm("2025.3")

        // The Database Tools & SQL plugin provides:
        //   • SqlDialectMappings  – dialect-to-file/dir mappings
        //   • DbPsiFacade         – access to configured data sources
        //   • DbDataSource        – concrete data source type
        bundledPlugin("com.intellij.database")

        // Enables ./gradlew verifyPlugin (checks API compatibility)
        pluginVerifier()
    }

    testImplementation("org.junit.jupiter:junit-jupiter:5.10.0")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

intellijPlatform {
    pluginConfiguration {
        // sinceBuild / untilBuild control which IDE versions accept the plugin.
        // 241 = 2024.1,  253 = 2025.3,  263 = 2026.3
        ideaVersion {
            sinceBuild = "241"
            untilBuild = "263.*"
        }
    }
}

tasks.test {
    useJUnitPlatform()
}
