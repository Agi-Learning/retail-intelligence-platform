/*
=========================================================
Retail Intelligence Platform
Migration: V013
Purpose:
  - Grant selective CDC read access
  - Create an explicit PostgreSQL publication
  - Exclude credential data from CDC
=========================================================
*/

SET ROLE retail_owner;

/*
Schema visibility required for the initial Debezium snapshot.
*/

GRANT USAGE ON SCHEMA identity TO retail_cdc;
GRANT USAGE ON SCHEMA catalog TO retail_cdc;
GRANT USAGE ON SCHEMA inventory TO retail_cdc;
GRANT USAGE ON SCHEMA commerce TO retail_cdc;
GRANT USAGE ON SCHEMA payment TO retail_cdc;
GRANT USAGE ON SCHEMA outbox TO retail_cdc;
GRANT USAGE ON SCHEMA audit TO retail_cdc;

/*
Identity credentials are deliberately excluded.
Password hashes must not enter Kafka or the analytical platform.
*/

GRANT SELECT
    ON TABLE identity.customers
    TO retail_cdc;

GRANT SELECT
    ON TABLE identity.addresses
    TO retail_cdc;

GRANT SELECT
    ON TABLE catalog.brands
    TO retail_cdc;

GRANT SELECT
    ON TABLE catalog.categories
    TO retail_cdc;

GRANT SELECT
    ON TABLE catalog.products
    TO retail_cdc;

GRANT SELECT
    ON TABLE catalog.product_prices
    TO retail_cdc;

GRANT SELECT
    ON TABLE inventory.warehouses
    TO retail_cdc;

GRANT SELECT
    ON TABLE inventory.stock
    TO retail_cdc;

GRANT SELECT
    ON TABLE inventory.reservations
    TO retail_cdc;

GRANT SELECT
    ON TABLE commerce.carts
    TO retail_cdc;

GRANT SELECT
    ON TABLE commerce.cart_items
    TO retail_cdc;

GRANT SELECT
    ON TABLE commerce.orders
    TO retail_cdc;

GRANT SELECT
    ON TABLE commerce.order_items
    TO retail_cdc;

GRANT SELECT
    ON TABLE commerce.order_addresses
    TO retail_cdc;

GRANT SELECT
    ON TABLE commerce.order_status_history
    TO retail_cdc;

GRANT SELECT
    ON TABLE payment.payments
    TO retail_cdc;

GRANT SELECT
    ON TABLE payment.payment_attempts
    TO retail_cdc;

GRANT SELECT
    ON TABLE payment.payment_status_history
    TO retail_cdc;

GRANT SELECT
    ON TABLE outbox.events
    TO retail_cdc;

GRANT SELECT
    ON TABLE audit.audit_events
    TO retail_cdc;

/*
The publication is owned by retail_owner because that role owns
all participating tables. Debezium uses this existing publication
and is not allowed to change its membership.
*/

CREATE PUBLICATION retail_cdc_publication
    FOR TABLE
        identity.customers,
        identity.addresses,

        catalog.brands,
        catalog.categories,
        catalog.products,
        catalog.product_prices,

        inventory.warehouses,
        inventory.stock,
        inventory.reservations,

        commerce.carts,
        commerce.cart_items,
        commerce.orders,
        commerce.order_items,
        commerce.order_addresses,
        commerce.order_status_history,

        payment.payments,
        payment.payment_attempts,
        payment.payment_status_history,

        outbox.events,
        audit.audit_events
    WITH (
        publish = 'insert, update, delete, truncate'
    );

COMMENT ON PUBLICATION retail_cdc_publication IS
    'Selective Debezium CDC publication excluding credential and migration data.';

RESET ROLE;