import org.gradle.api.initialization.resolve.RepositoriesMode

pluginManagement {
    includeBuild("build-logic")

    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(
        RepositoriesMode.FAIL_ON_PROJECT_REPOS,
    )

    repositories {
        mavenCentral()
    }
}

rootProject.name = "retail-intelligence-backend"

include(
    ":platform:dependency-bom",
    ":platform:service-starter",
    ":platform:security-starter",
    ":platform:kafka-starter",
    ":platform:observability-starter",
    ":platform:testing-starter",
    ":services:identity-service",
)
