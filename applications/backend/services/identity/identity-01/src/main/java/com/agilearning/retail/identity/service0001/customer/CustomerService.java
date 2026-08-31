package com.agilearning.retail.identity.service0001.customer;

import java.time.Instant;
import java.util.Locale;
import java.util.UUID;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class CustomerService {

    private final CustomerRepository repository;

    public CustomerService(CustomerRepository repository) {
        this.repository = repository;
    }

    public CustomerResponse create(CreateCustomerRequest request) {
        String email = request.email().trim().toLowerCase(Locale.ROOT);

        if (repository.existsByEmail(email)) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "Customer email already exists"
            );
        }

        Instant now = Instant.now();
        Customer customer = new Customer(
                null,
                UUID.randomUUID(),
                request.firstName().trim(),
                normalize(request.lastName()),
                email,
                normalize(request.phoneNumber()),
                "PENDING",
                now,
                null,
                now,
                now,
                null,
                0L
        );

        return CustomerResponse.from(repository.save(customer));
    }

    public CustomerResponse find(UUID publicId) {
        return repository.findByPublicId(publicId)
                .filter(customer -> customer.deletedAt() == null)
                .map(CustomerResponse::from)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "Customer not found"
                ));
    }

    private static String normalize(String value) {
        if (value == null) {
            return null;
        }

        String normalized = value.trim();
        return normalized.isEmpty() ? null : normalized;
    }
}
