package com.agilearning.retail.identity.service0001.customer;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.UUID;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

@ExtendWith(MockitoExtension.class)
class CustomerControllerTest {

    @Mock
    private CustomerService service;

    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        mvc = MockMvcBuilders
                .standaloneSetup(new CustomerController(service))
                .build();
    }

    @Test
    void createsCustomerAtContractPath() throws Exception {
        UUID publicId = UUID.randomUUID();

        when(service.create(any(CreateCustomerRequest.class)))
                .thenReturn(new CustomerResponse(
                        publicId,
                        "User",
                        null,
                        "user@example.com",
                        null,
                        "PENDING",
                        null,
                        null
                ));

        mvc.perform(post("/api/v1/identity/01/customers")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "firstName": "User",
                                  "email": "user@example.com"
                                }
                                """))
                .andExpect(status().isCreated())
                .andExpect(header().string(
                        "Location",
                        "/api/v1/identity/01/customers/" + publicId
                ))
                .andExpect(jsonPath("$.publicId").value(publicId.toString()));
    }

    @Test
    void readsCustomerAtContractPath() throws Exception {
        UUID publicId = UUID.randomUUID();

        when(service.find(publicId))
                .thenReturn(new CustomerResponse(
                        publicId,
                        "User",
                        null,
                        "user@example.com",
                        null,
                        "PENDING",
                        null,
                        null
                ));

        mvc.perform(get("/api/v1/identity/01/customers/" + publicId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.email").value("user@example.com"));
    }
}
