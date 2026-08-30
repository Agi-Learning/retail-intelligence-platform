plugins {
    `java-library`
}

dependencies {
    api(
        platform(
            project(":platform:dependency-bom")
        )
    )

    api(
        "org.springframework.boot:"
            + "spring-boot-starter-actuator"
    )
    api(
        "io.micrometer:"
            + "micrometer-registry-prometheus"
    )
}