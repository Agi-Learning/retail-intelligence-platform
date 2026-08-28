/*
=========================================================
Retail Intelligence Platform
Migration: V003
Purpose:
  - Correct ownership of V002 Identity objects
  - Apply runtime privileges
  - Establish the ownership pattern for future migrations
=========================================================
*/

/*
The current Flyway login, retail_migration, created and owns
these tables. It can transfer them to retail_owner because it
is a member of retail_owner.
*/

ALTER TABLE identity.customers
    OWNER TO retail_owner;

ALTER TABLE identity.credentials
    OWNER TO retail_owner;

ALTER TABLE identity.addresses
    OWNER TO retail_owner;

/*
From this point onward, perform owner-specific operations as
retail_owner.
*/

SET ROLE retail_owner;

/*
Identity columns created corresponding sequences.
Explicitly assign them to retail_owner.
*/

ALTER SEQUENCE identity.customers_customer_id_seq
    OWNER TO retail_owner;

ALTER SEQUENCE identity.credentials_credential_id_seq
    OWNER TO retail_owner;

ALTER SEQUENCE identity.addresses_address_id_seq
    OWNER TO retail_owner;

/*
Grant runtime privileges because V002 objects were originally
created as retail_migration, so retail_owner's default privileges
did not apply to them.
*/

GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLE identity.customers
    TO retail_app;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLE identity.credentials
    TO retail_app;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLE identity.addresses
    TO retail_app;

GRANT USAGE, SELECT
    ON SEQUENCE identity.customers_customer_id_seq
    TO retail_app;

GRANT USAGE, SELECT
    ON SEQUENCE identity.credentials_credential_id_seq
    TO retail_app;

GRANT USAGE, SELECT
    ON SEQUENCE identity.addresses_address_id_seq
    TO retail_app;

RESET ROLE;