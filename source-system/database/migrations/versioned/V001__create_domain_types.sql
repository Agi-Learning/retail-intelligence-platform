/*
=========================================================
Retail Intelligence Platform
Migration: V001
Purpose: Create strongly typed business-state enumerations
=========================================================
*/

SET ROLE retail_owner;

/*
=========================================================
IDENTITY TYPES
=========================================================
*/

CREATE TYPE identity.customer_status AS ENUM (
    'PENDING',
    'ACTIVE',
    'LOCKED',
    'SUSPENDED',
    'CLOSED'
);

COMMENT ON TYPE identity.customer_status IS
    'Current lifecycle state of a customer account.';

CREATE TYPE identity.address_type AS ENUM (
    'HOME',
    'WORK',
    'BILLING',
    'SHIPPING',
    'OTHER'
);

COMMENT ON TYPE identity.address_type IS
    'Business classification of a customer address.';

/*
=========================================================
CATALOGUE TYPES
=========================================================
*/

CREATE TYPE catalog.product_status AS ENUM (
    'DRAFT',
    'ACTIVE',
    'INACTIVE',
    'DISCONTINUED'
);

COMMENT ON TYPE catalog.product_status IS
    'Current lifecycle state of a catalogue product.';

/*
=========================================================
COMMERCE TYPES
=========================================================
*/

CREATE TYPE commerce.cart_status AS ENUM (
    'ACTIVE',
    'CHECKED_OUT',
    'ABANDONED',
    'EXPIRED'
);

COMMENT ON TYPE commerce.cart_status IS
    'Current lifecycle state of a shopping cart.';

CREATE TYPE commerce.order_status AS ENUM (
    'PENDING',
    'INVENTORY_RESERVED',
    'PAYMENT_PENDING',
    'CONFIRMED',
    'PROCESSING',
    'SHIPPED',
    'DELIVERED',
    'CANCELLED',
    'RETURN_REQUESTED',
    'RETURNED',
    'REFUNDED'
);

COMMENT ON TYPE commerce.order_status IS
    'Current lifecycle state of an order.';

/*
=========================================================
INVENTORY TYPES
=========================================================
*/

CREATE TYPE inventory.reservation_status AS ENUM (
    'PENDING',
    'RESERVED',
    'RELEASED',
    'CONSUMED',
    'REJECTED',
    'EXPIRED'
);

COMMENT ON TYPE inventory.reservation_status IS
    'Current state of an inventory reservation.';

/*
=========================================================
PAYMENT TYPES
=========================================================
*/

CREATE TYPE payment.payment_status AS ENUM (
    'INITIATED',
    'PROCESSING',
    'SUCCEEDED',
    'FAILED',
    'CANCELLED',
    'REFUNDED',
    'PARTIALLY_REFUNDED'
);

COMMENT ON TYPE payment.payment_status IS
    'Current lifecycle state of a payment.';

/*
=========================================================
OUTBOX TYPES
=========================================================
*/

CREATE TYPE outbox.event_status AS ENUM (
    'PENDING',
    'PUBLISHED',
    'FAILED',
    'DEAD'
);

COMMENT ON TYPE outbox.event_status IS
    'Publication state of a transactional Outbox event.';

RESET ROLE;