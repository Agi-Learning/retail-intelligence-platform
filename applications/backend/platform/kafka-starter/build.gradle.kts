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
        "org.springframework.kafka:"
            + "spring-kafka"
    )
}