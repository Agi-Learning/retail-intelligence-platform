package com.agilearning.retail.identity;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.boot.autoconfigure.SpringBootApplication;

class IdentityServiceApplicationTest {

    @Test
    void applicationEntryPointIsSpringBootApplication() {
        assertThat(
                IdentityServiceApplication.class.isAnnotationPresent(
                    SpringBootApplication.class
                )
            )
            .isTrue();
    }
}
