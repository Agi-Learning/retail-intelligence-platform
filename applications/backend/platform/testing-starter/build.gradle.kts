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
            + "spring-boot-starter-test"
    )
    api(
        "org.testcontainers:"
            + "testcontainers-junit-jupiter"
    )
}