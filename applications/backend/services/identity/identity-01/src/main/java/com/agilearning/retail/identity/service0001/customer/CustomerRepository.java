package com.agilearning.retail.identity.service0001.customer;

import java.util.Optional;
import java.util.UUID;

import org.springframework.data.repository.CrudRepository;

public interface CustomerRepository extends CrudRepository<Customer, Long> {

    Optional<Customer> findByPublicId(UUID publicId);

    boolean existsByEmail(String email);
}
