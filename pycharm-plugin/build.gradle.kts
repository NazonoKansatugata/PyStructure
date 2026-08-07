import org.jetbrains.kotlin.gradle.tasks.KotlinCompile

plugins {
    kotlin("jvm") version "1.9.24"
    id("org.jetbrains.intellij") version "1.17.4"
}

group = "com.pystructure"
version = providers.gradleProperty("pluginVersion").get()

repositories {
    mavenCentral()
}

intellij {
    version.set(providers.gradleProperty("platformVersion").get())
    type.set("IC")
}

dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")
}

tasks {
    patchPluginXml {
        sinceBuild.set("241")
        untilBuild.set("241.*")
    }

    withType<KotlinCompile> {
        kotlinOptions.jvmTarget = "17"
    }
}
