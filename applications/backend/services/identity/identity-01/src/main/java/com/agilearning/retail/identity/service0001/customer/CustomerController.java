package com.agilearning.retail.identity.service0001.customer;

import java.net.URI;
import java.util.UUID;

import jakarta.validation.Valid;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("${app.api-base-path:/api/v1/identity/01}/customers")
public class CustomerController {

    private final CustomerService service;

    public CustomerController(CustomerService service) {
        this.service = service;
    }

    @PostMapping
    ResponseEntity<CustomerResponse> create(
            @Valid @RequestBody CreateCustomerRequest request
    ) {
        CustomerResponse response = service.create(request);

        return ResponseEntity
                .created(URI.create(
                        "/api/v1/identity/01/customers/" + response.publicId()
                ))
                .body(response);
    }

    @GetMapping("/{publicId}")
    CustomerResponse find(@PathVariable UUID publicId) {
        return service.find(publicId);
    }
}
