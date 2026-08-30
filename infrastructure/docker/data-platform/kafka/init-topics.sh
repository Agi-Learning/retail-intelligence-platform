#!/usr/bin/env bash

set -Eeuo pipefail

readonly BOOTSTRAP_SERVER="retail-kafka:29092"
readonly BUSINESS_RETENTION_MS="604800000"

create_topic() {
    local topic_name="$1"
    local partitions="$2"
    local cleanup_policy="$3"
    local retention_ms="$4"

    /opt/kafka/bin/kafka-topics.sh \
        --bootstrap-server "${BOOTSTRAP_SERVER}" \
        --create \
        --if-not-exists \
        --topic "${topic_name}" \
        --partitions "${partitions}" \
        --replication-factor 1

    /opt/kafka/bin/kafka-configs.sh \
        --bootstrap-server "${BOOTSTRAP_SERVER}" \
        --entity-type topics \
        --entity-name "${topic_name}" \
        --alter \
        --add-config \
        "cleanup.policy=${cleanup_policy},retention.ms=${retention_ms}"
}

echo "Creating Kafka Connect internal topics"

create_topic \
    "retail.connect.configs" \
    1 \
    "compact" \
    "-1"

create_topic \
    "retail.connect.offsets" \
    3 \
    "compact" \
    "-1"

create_topic \
    "retail.connect.status" \
    3 \
    "compact" \
    "-1"

readonly CDC_TOPICS=(
    "retail.cdc.identity.customers"
    "retail.cdc.identity.addresses"

    "retail.cdc.catalog.brands"
    "retail.cdc.catalog.categories"
    "retail.cdc.catalog.products"
    "retail.cdc.catalog.product_prices"

    "retail.cdc.inventory.warehouses"
    "retail.cdc.inventory.stock"
    "retail.cdc.inventory.reservations"

    "retail.cdc.commerce.carts"
    "retail.cdc.commerce.cart_items"
    "retail.cdc.commerce.orders"
    "retail.cdc.commerce.order_items"
    "retail.cdc.commerce.order_addresses"
    "retail.cdc.commerce.order_status_history"

    "retail.cdc.payment.payments"
    "retail.cdc.payment.payment_attempts"
    "retail.cdc.payment.payment_status_history"

    "retail.cdc.outbox.events"
    "retail.cdc.audit.audit_events"
)

echo "Creating CDC business topics"

for topic_name in "${CDC_TOPICS[@]}"; do
    create_topic \
        "${topic_name}" \
        3 \
        "delete" \
        "${BUSINESS_RETENTION_MS}"
done

echo "Kafka topic initialization completed"