plugins {
    `java-platform`
}

javaPlatform {
    allowDependencies()
}

dependencies {
    api(
        platform(
            "org.springframework.boot:"
                + "spring-boot-dependencies:4.1.1"
        )
    )
    api(
        platform(
            "org.testcontainers:"
                + "testcontainers-bom:2.0.5"
        )
    )
}