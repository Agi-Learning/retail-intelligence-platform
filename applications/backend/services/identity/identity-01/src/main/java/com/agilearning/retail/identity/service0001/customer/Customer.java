package com.agilearning.retail.identity.service0001.customer;

import java.time.Instant;
import java.util.UUID;

import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.Version;
import org.springframework.data.relational.core.mapping.Column;
import org.springframework.data.relational.core.mapping.Table;

@Table(value = "customers", schema = "identity")
public record Customer(
        @Id @Column("customer_id") Long customerId,
        @Column("public_id") UUID publicId,
        @Column("first_name") String firstName,
        @Column("last_name") String lastName,
        @Column("email") String email,
        @Column("phone_number") String phoneNumber,
        @Column("status") String status,
        @Column("registered_at") Instant registeredAt,
        @Column("last_login_at") Instant lastLoginAt,
        @Column("created_at") Instant createdAt,
        @Column("updated_at") Instant updatedAt,
        @Column("deleted_at") Instant deletedAt,
        @Version @Column("version") Long version
) {}
