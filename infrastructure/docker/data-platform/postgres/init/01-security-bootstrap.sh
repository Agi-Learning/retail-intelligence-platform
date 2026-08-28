#!/usr/bin/env bash

set -euo pipefail

read_secret() {
    local secret_file="$1"

    if [[ ! -f "$secret_file" ]]; then
        echo "Required secret file is missing: $secret_file" >&2
        exit 1
    fi

    tr -d '\r\n' < "$secret_file"
}

migration_password="$(read_secret /run/secrets/postgres_migration_password)"
app_password="$(read_secret /run/secrets/postgres_app_password)"
cdc_password="$(read_secret /run/secrets/postgres_cdc_password)"
loader_password="$(read_secret /run/secrets/postgres_loader_password)"
analyst_password="$(read_secret /run/secrets/postgres_analyst_password)"
monitor_password="$(read_secret /run/secrets/postgres_monitor_password)"

psql \
    --set ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" \
    --set migration_password="$migration_password" \
    --set app_password="$app_password" \
    --set cdc_password="$cdc_password" \
    --set loader_password="$loader_password" \
    --set analyst_password="$analyst_password" \
    --set monitor_password="$monitor_password" <<'SQL'
/*
=========================================================
DATABASE SECURITY
=========================================================
*/

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE retail_platform FROM PUBLIC;

/*
The owner role cannot log in directly.
Application processes never receive this role's password.
*/

CREATE ROLE retail_owner
    NOLOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION;

/*
Flyway migration role.
It can assume the object-owner role during controlled migrations.
*/

CREATE ROLE retail_migration
    LOGIN
    PASSWORD :'migration_password'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION;

GRANT retail_owner TO retail_migration;

/*
Spring Boot runtime role.
No schema-creation or table-dropping privileges.
*/

CREATE ROLE retail_app
    LOGIN
    PASSWORD :'app_password'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION;

/*
Debezium logical-replication role.
Table access will be granted selectively later.
*/

CREATE ROLE retail_cdc
    LOGIN
    REPLICATION
    PASSWORD :'cdc_password'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE;

/*
Historical bulk-data loading role.
*/

CREATE ROLE retail_loader
    LOGIN
    PASSWORD :'loader_password'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION;

/*
Read-only analytical user.
Access will be limited to approved views later.
*/

CREATE ROLE retail_analyst
    LOGIN
    PASSWORD :'analyst_password'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION;

/*
Monitoring role.
pg_monitor provides database statistics without superuser access.
*/

CREATE ROLE retail_monitor
    LOGIN
    PASSWORD :'monitor_password'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION;

GRANT pg_monitor TO retail_monitor;

/*
=========================================================
DATABASE CONNECTION PRIVILEGES
=========================================================
*/

GRANT CONNECT ON DATABASE retail_platform TO retail_owner;
GRANT CONNECT ON DATABASE retail_platform TO retail_migration;
GRANT CONNECT ON DATABASE retail_platform TO retail_app;
GRANT CONNECT ON DATABASE retail_platform TO retail_cdc;
GRANT CONNECT ON DATABASE retail_platform TO retail_loader;
GRANT CONNECT ON DATABASE retail_platform TO retail_analyst;
GRANT CONNECT ON DATABASE retail_platform TO retail_monitor;

/*
=========================================================
EXTENSIONS
=========================================================
*/

CREATE EXTENSION IF NOT EXISTS pgcrypto;

/*
=========================================================
DOMAIN SCHEMAS
=========================================================
*/

CREATE SCHEMA identity AUTHORIZATION retail_owner;
CREATE SCHEMA catalog AUTHORIZATION retail_owner;
CREATE SCHEMA inventory AUTHORIZATION retail_owner;
CREATE SCHEMA commerce AUTHORIZATION retail_owner;
CREATE SCHEMA payment AUTHORIZATION retail_owner;
CREATE SCHEMA fulfillment AUTHORIZATION retail_owner;
CREATE SCHEMA engagement AUTHORIZATION retail_owner;
CREATE SCHEMA outbox AUTHORIZATION retail_owner;
CREATE SCHEMA audit AUTHORIZATION retail_owner;
CREATE SCHEMA reference AUTHORIZATION retail_owner;
CREATE SCHEMA staging AUTHORIZATION retail_owner;

/*
=========================================================
SCHEMA VISIBILITY
=========================================================
*/

GRANT USAGE ON SCHEMA identity TO retail_app;
GRANT USAGE ON SCHEMA catalog TO retail_app;
GRANT USAGE ON SCHEMA inventory TO retail_app;
GRANT USAGE ON SCHEMA commerce TO retail_app;
GRANT USAGE ON SCHEMA payment TO retail_app;
GRANT USAGE ON SCHEMA fulfillment TO retail_app;
GRANT USAGE ON SCHEMA engagement TO retail_app;
GRANT USAGE ON SCHEMA outbox TO retail_app;
GRANT USAGE ON SCHEMA reference TO retail_app;

GRANT USAGE ON SCHEMA staging TO retail_loader;
GRANT USAGE ON SCHEMA reference TO retail_loader;

GRANT USAGE ON SCHEMA outbox TO retail_cdc;

GRANT USAGE ON SCHEMA reference TO retail_analyst;

GRANT USAGE ON SCHEMA identity TO retail_monitor;
GRANT USAGE ON SCHEMA catalog TO retail_monitor;
GRANT USAGE ON SCHEMA inventory TO retail_monitor;
GRANT USAGE ON SCHEMA commerce TO retail_monitor;
GRANT USAGE ON SCHEMA payment TO retail_monitor;
GRANT USAGE ON SCHEMA fulfillment TO retail_monitor;
GRANT USAGE ON SCHEMA engagement TO retail_monitor;
GRANT USAGE ON SCHEMA outbox TO retail_monitor;
GRANT USAGE ON SCHEMA audit TO retail_monitor;

/*
=========================================================
DEFAULT PRIVILEGES FOR FUTURE TABLES
=========================================================
*/

ALTER DEFAULT PRIVILEGES FOR ROLE retail_owner
    IN SCHEMA identity
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO retail_app;

ALTER DEFAULT PRIVILEGES FOR ROLE retail_owner
    IN SCHEMA catalog
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO retail_app;

ALTER DEFAULT PRIVILEGES FOR ROLE retail_owner
    IN SCHEMA inventory
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO retail_app;

ALTER DEFAULT PRIVILEGES FOR ROLE retail_owner
    IN SCHEMA commerce
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO retail_app;

ALTER DEFAULT PRIVILEGES FOR ROLE retail_owner
    IN SCHEMA payment
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO retail_app;

ALTER DEFAULT PRIVILEGES FOR ROLE retail_owner
    IN SCHEMA fulfillment
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO retail_app;

ALTER DEFAULT PRIVILEGES FOR ROLE retail_owner
    IN SCHEMA engagement
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO retail_app;

ALTER DEFAULT PRIVILEGES FOR ROLE retail_owner
    IN SCHEMA outbox
    GRANT SELECT, INSERT, UPDATE ON TABLES TO retail_app;

ALTER DEFAULT PRIVILEGES FOR ROLE retail_owner
    IN SCHEMA reference
    GRANT SELECT ON TABLES TO retail_app;

ALTER DEFAULT PRIVILEGES FOR ROLE retail_owner
    IN SCHEMA staging
    GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE
    ON TABLES TO retail_loader;

/*
Sequences generated for BIGINT identity columns also need privileges.
*/

ALTER DEFAULT PRIVILEGES FOR ROLE retail_owner
    IN SCHEMA identity
    GRANT USAGE, SELECT ON SEQUENCES TO retail_app;

ALTER DEFAULT PRIVILEGES FOR ROLE retail_owner
    IN SCHEMA catalog
    GRANT USAGE, SELECT ON SEQUENCES TO retail_app;

ALTER DEFAULT PRIVILEGES FOR ROLE retail_owner
    IN SCHEMA inventory
    GRANT USAGE, SELECT ON SEQUENCES TO retail_app;

ALTER DEFAULT PRIVILEGES FOR ROLE retail_owner
    IN SCHEMA commerce
    GRANT USAGE, SELECT ON SEQUENCES TO retail_app;

ALTER DEFAULT PRIVILEGES FOR ROLE retail_owner
    IN SCHEMA payment
    GRANT USAGE, SELECT ON SEQUENCES TO retail_app;

ALTER DEFAULT PRIVILEGES FOR ROLE retail_owner
    IN SCHEMA fulfillment
    GRANT USAGE, SELECT ON SEQUENCES TO retail_app;

ALTER DEFAULT PRIVILEGES FOR ROLE retail_owner
    IN SCHEMA engagement
    GRANT USAGE, SELECT ON SEQUENCES TO retail_app;

/*
=========================================================
ROLE DEFAULTS
=========================================================
*/

ALTER ROLE retail_app SET timezone = 'UTC';
ALTER ROLE retail_migration SET timezone = 'UTC';
ALTER ROLE retail_cdc SET timezone = 'UTC';
ALTER ROLE retail_loader SET timezone = 'UTC';
ALTER ROLE retail_analyst SET timezone = 'UTC';
ALTER ROLE retail_monitor SET timezone = 'UTC';

ALTER ROLE retail_app
    SET statement_timeout = '30s';

ALTER ROLE retail_analyst
    SET statement_timeout = '5min';

ALTER ROLE retail_loader
    SET statement_timeout = '0';

ALTER DATABASE retail_platform
    SET timezone = 'UTC';

COMMENT ON DATABASE retail_platform IS
    'Operational database for the Retail Intelligence platform.';
SQL

unset migration_password
unset app_password
unset cdc_password
unset loader_password
unset analyst_password
unset monitor_password