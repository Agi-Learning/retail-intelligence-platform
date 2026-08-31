plugins {
    `java-library`
}

dependencies {
    api(
        platform(
            project(":platform:dependency-bom")
        )
    )

    api("org.springframework.boot:spring-boot-starter-web")
    api(
        "org.springframework.boot:"
            + "spring-boot-starter-validation"
    )
    api(
        "org.springframework.boot:"
            + "spring-boot-starter-data-jdbc"
    )
    api(
        "org.springframework.boot:"
            + "spring-boot-starter-actuator"
    )
    api("org.flywaydb:flyway-core")
}