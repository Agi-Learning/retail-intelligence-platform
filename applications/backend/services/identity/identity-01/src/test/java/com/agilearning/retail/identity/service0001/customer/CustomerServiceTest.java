package com.agilearning.retail.identity.service0001.customer;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.server.ResponseStatusException;

@ExtendWith(MockitoExtension.class)
class CustomerServiceTest {

    @Mock
    private CustomerRepository repository;

    @InjectMocks
    private CustomerService service;

    @Test
    void createsNormalizedCustomer() {
        when(repository.existsByEmail("user@example.com")).thenReturn(false);
        when(repository.save(any(Customer.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));

        CustomerResponse response = service.create(
                new CreateCustomerRequest(
                        "  User ",
                        "  Customer ",
                        " USER@EXAMPLE.COM ",
                        "  +919999999999 "
                )
        );

        assertThat(response.email()).isEqualTo("user@example.com");
        assertThat(response.firstName()).isEqualTo("User");
        assertThat(response.lastName()).isEqualTo("Customer");
        assertThat(response.status()).isEqualTo("PENDING");
        verify(repository).save(any(Customer.class));
    }

    @Test
    void rejectsDuplicateEmail() {
        when(repository.existsByEmail("user@example.com")).thenReturn(true);

        assertThatThrownBy(() -> service.create(
                new CreateCustomerRequest(
                        "User",
                        null,
                        "user@example.com",
                        null
                )
        ))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("Customer email already exists");
    }

    @Test
    void findsActiveCustomerByPublicId() {
        UUID publicId = UUID.randomUUID();
        Customer customer = new Customer(
                1L,
                publicId,
                "User",
                null,
                "user@example.com",
                null,
                "PENDING",
                null,
                null,
                null,
                null,
                null,
                0L
        );

        when(repository.findByPublicId(publicId))
                .thenReturn(java.util.Optional.of(customer));

        assertThat(service.find(publicId).publicId()).isEqualTo(publicId);
    }
}
