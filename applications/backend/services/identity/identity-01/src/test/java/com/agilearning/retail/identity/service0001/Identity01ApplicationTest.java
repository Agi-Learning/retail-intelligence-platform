package com.agilearning.retail.identity.service0001;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.boot.autoconfigure.SpringBootApplication;

class Identity01ApplicationTest {

    @Test
    void applicationEntryPointIsSpringBootApplication() {
        assertThat(
                Identity01Application.class.isAnnotationPresent(
                    SpringBootApplication.class
                )
            )
            .isTrue();
    }
}
