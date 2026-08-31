plugins {
    id("retail.java-service-conventions")
    alias(libs.plugins.spring.boot)
}

dependencies {
    runtimeOnly("org.postgresql:postgresql")

    implementation(project(":platform:service-starter"))
    implementation(project(":platform:security-starter"))
    implementation(project(":platform:kafka-starter"))
    implementation(project(":platform:observability-starter"))
    testImplementation(project(":platform:testing-starter"))
}
