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
            + "spring-boot-starter-security"
    )
    api(
        "org.springframework.boot:"
            + "spring-boot-starter-oauth2-resource-server"
    )
    api(
        "org.springframework.security:"
            + "spring-security-oauth2-jose"
    )
}