package com.agilearning.retail.identity.service0001.customer;

import java.time.Instant;
import java.util.UUID;

public record CustomerResponse(
        UUID publicId,
        String firstName,
        String lastName,
        String email,
        String phoneNumber,
        String status,
        Instant registeredAt,
        Instant lastLoginAt
) {
    static CustomerResponse from(Customer customer) {
        return new CustomerResponse(
                customer.publicId(),
                customer.firstName(),
                customer.lastName(),
                customer.email(),
                customer.phoneNumber(),
                customer.status(),
                customer.registeredAt(),
                customer.lastLoginAt()
        );
    }
}
