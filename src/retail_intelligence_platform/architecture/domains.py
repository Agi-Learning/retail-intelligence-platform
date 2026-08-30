"""Generation of the enterprise domain implementation manifest."""

from collections import Counter, defaultdict
from csv import DictReader, DictWriter
from dataclasses import dataclass
from pathlib import Path

EXPECTED_DOMAINS = 100
EXPECTED_SERVICES = 1_000
EXPECTED_TABLES = 10_000
EXPECTED_RELATIONSHIPS = 6_040

DOMAIN_MANIFEST_COLUMNS = (
    "lesson_number",
    "domain_id",
    "domain",
    "service_group",
    "service_count",
    "microservice_ids",
    "microservice_names",
    "team_count",
    "team_ids",
    "database_count",
    "database_names",
    "cluster_count",
    "db_clusters",
    "table_count",
    "full_cdc_table_count",
    "excluded_cdc_table_count",
    "outgoing_relationship_count",
    "incoming_relationship_count",
    "colocated_logical_reference_count",
    "event_driven_reference_count",
    "event_topic_count",
    "dlq_topic_count",
    "backend_domain_path",
    "api_gateway_base_path",
    "customer_frontend_path",
    "admin_frontend_path",
    "frontend_exposure_policy",
    "docker_profile",
    "deployment_namespace",
    "implementation_status",
)


class DomainManifestError(ValueError):
    """Raised when a domain implementation manifest is invalid."""


@dataclass(frozen=True, slots=True)
class DomainManifestSummary:
    """Validated measurements from the domain manifest."""

    domains: int
    services: int
    tables: int
    databases: int
    outgoing_relationships: int
    incoming_relationships: int
    colocated_logical_references: int
    event_driven_references: int
    event_topics: int
    dlq_topics: int
    frontend_policies_pending: int


def write_domain_manifest(
    service_manifest_path: Path,
    relationship_manifest_path: Path,
    destination: Path,
) -> int:
    """Aggregate services and relationships into domain plans."""

    services = _read_csv(service_manifest_path)
    relationships = _read_csv(relationship_manifest_path)

    if len(services) != EXPECTED_SERVICES:
        raise DomainManifestError(
            f"Expected {EXPECTED_SERVICES} services, found {len(services)}"
        )

    if len(relationships) != EXPECTED_RELATIONSHIPS:
        raise DomainManifestError(
            f"Expected {EXPECTED_RELATIONSHIPS} relationships, "
            f"found {len(relationships)}"
        )

    services_by_domain: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for service in services:
        services_by_domain[service["domain"]].append(service)

    outgoing_by_domain: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    incoming_by_domain: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for relationship in relationships:
        outgoing_by_domain[relationship["source_domain"]].append(relationship)

        incoming_by_domain[relationship["target_domain"]].append(relationship)

    rows = [
        _build_domain_row(
            domain,
            domain_services,
            outgoing_by_domain[domain],
            incoming_by_domain[domain],
        )
        for domain, domain_services in sorted(services_by_domain.items())
    ]

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with destination.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = DictWriter(
            stream,
            fieldnames=DOMAIN_MANIFEST_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(rows)  # type: ignore[arg-type]

    return len(rows)


def validate_domain_manifest(
    path: Path,
) -> DomainManifestSummary:
    """Validate domain ownership and relationship totals."""

    with path.open(
        newline="",
        encoding="utf-8",
    ) as stream:
        reader = DictReader(stream)
        rows = list(reader)
        columns = tuple(reader.fieldnames or ())

    if columns != DOMAIN_MANIFEST_COLUMNS:
        raise DomainManifestError("Unexpected domain manifest columns")

    if len(rows) != EXPECTED_DOMAINS:
        raise DomainManifestError(
            f"Expected {EXPECTED_DOMAINS} domains, found {len(rows)}"
        )

    domains = {row["domain"] for row in rows}

    domain_ids = {row["domain_id"] for row in rows}

    backend_paths = {row["backend_domain_path"] for row in rows}

    api_paths = {row["api_gateway_base_path"] for row in rows}

    if len(domains) != EXPECTED_DOMAINS:
        raise DomainManifestError("Domain names are not unique")

    if len(domain_ids) != EXPECTED_DOMAINS:
        raise DomainManifestError("Domain identifiers are not unique")

    if len(backend_paths) != EXPECTED_DOMAINS:
        raise DomainManifestError("Backend domain paths are not unique")

    if len(api_paths) != EXPECTED_DOMAINS:
        raise DomainManifestError("API gateway paths are not unique")

    _validate_rows(rows)

    services = sum(int(row["service_count"]) for row in rows)

    tables = sum(int(row["table_count"]) for row in rows)

    databases = sum(int(row["database_count"]) for row in rows)

    outgoing = sum(int(row["outgoing_relationship_count"]) for row in rows)

    incoming = sum(int(row["incoming_relationship_count"]) for row in rows)

    colocated = sum(int(row["colocated_logical_reference_count"]) for row in rows)

    event_driven = sum(int(row["event_driven_reference_count"]) for row in rows)

    event_topics = sum(int(row["event_topic_count"]) for row in rows)

    dlq_topics = sum(int(row["dlq_topic_count"]) for row in rows)

    frontend_pending = sum(
        row["frontend_exposure_policy"] == "POLICY_PENDING" for row in rows
    )

    expected_totals = {
        "services": (
            services,
            EXPECTED_SERVICES,
        ),
        "tables": (
            tables,
            EXPECTED_TABLES,
        ),
        "databases": (
            databases,
            EXPECTED_SERVICES,
        ),
        "outgoing relationships": (
            outgoing,
            EXPECTED_RELATIONSHIPS,
        ),
        "incoming relationships": (
            incoming,
            EXPECTED_RELATIONSHIPS,
        ),
        "effective relationships": (
            colocated + event_driven,
            EXPECTED_RELATIONSHIPS,
        ),
    }

    for name, (actual, expected) in expected_totals.items():
        if actual != expected:
            raise DomainManifestError(f"Expected {expected} {name}, found {actual}")

    return DomainManifestSummary(
        domains=len(rows),
        services=services,
        tables=tables,
        databases=databases,
        outgoing_relationships=outgoing,
        incoming_relationships=incoming,
        colocated_logical_references=colocated,
        event_driven_references=event_driven,
        event_topics=event_topics,
        dlq_topics=dlq_topics,
        frontend_policies_pending=frontend_pending,
    )


def _build_domain_row(
    domain: str,
    services: list[dict[str, str]],
    outgoing: list[dict[str, str]],
    incoming: list[dict[str, str]],
) -> dict[str, str]:
    _require_single_value(
        domain,
        services,
        "domain_id",
    )
    _require_single_value(
        domain,
        services,
        "service_group",
    )

    service_ids = sorted({service["microservice_id"] for service in services})

    service_names = sorted({service["microservice_name"] for service in services})

    team_ids = sorted({service["team_id"] for service in services})

    databases = sorted({service["database_name"] for service in services})

    clusters = sorted(
        {
            cluster
            for service in services
            for cluster in service["db_clusters"].split("|")
            if cluster
        }
    )

    full_cdc_tables = sum(int(service["full_cdc_table_count"]) for service in services)

    excluded_cdc_tables = sum(
        int(service["excluded_cdc_table_count"]) for service in services
    )

    implementation_counts = Counter(
        relationship["effective_implementation"] for relationship in outgoing
    )

    event_topics = {
        relationship["event_topic"]
        for relationship in outgoing
        if relationship["kafka_required"] == "Y"
    }

    dlq_topics = {
        relationship["dlq_topic"]
        for relationship in outgoing
        if relationship["dlq_topic"]
    }

    return {
        "lesson_number": "127",
        "domain_id": services[0]["domain_id"],
        "domain": domain,
        "service_group": services[0]["service_group"],
        "service_count": str(len(service_ids)),
        "microservice_ids": "|".join(service_ids),
        "microservice_names": "|".join(service_names),
        "team_count": str(len(team_ids)),
        "team_ids": "|".join(team_ids),
        "database_count": str(len(databases)),
        "database_names": "|".join(databases),
        "cluster_count": str(len(clusters)),
        "db_clusters": "|".join(clusters),
        "table_count": str(
            sum(int(service["owned_table_count"]) for service in services)
        ),
        "full_cdc_table_count": str(full_cdc_tables),
        "excluded_cdc_table_count": str(excluded_cdc_tables),
        "outgoing_relationship_count": str(len(outgoing)),
        "incoming_relationship_count": str(len(incoming)),
        "colocated_logical_reference_count": str(
            implementation_counts["COLOCATED_LOGICAL_REFERENCE"]
        ),
        "event_driven_reference_count": str(
            implementation_counts["EVENT_DRIVEN_LOGICAL_REFERENCE"]
        ),
        "event_topic_count": str(len(event_topics)),
        "dlq_topic_count": str(len(dlq_topics)),
        "backend_domain_path": (f"applications/backend/services/{domain}"),
        "api_gateway_base_path": f"/api/v1/{domain}",
        "customer_frontend_path": (
            f"applications/frontend/customer-web/src/domains/{domain}"
        ),
        "admin_frontend_path": (
            f"applications/frontend/admin-web/src/domains/{domain}"
        ),
        "frontend_exposure_policy": "POLICY_PENDING",
        "docker_profile": f"domain-{domain}",
        "deployment_namespace": f"retail-{domain}",
        "implementation_status": "PLANNED",
    }


def _validate_rows(
    rows: list[dict[str, str]],
) -> None:
    for row in rows:
        if row["lesson_number"] != "127":
            raise DomainManifestError(f"{row['domain']} has an invalid lesson")

        if int(row["service_count"]) != 10:
            raise DomainManifestError(f"{row['domain']} does not own 10 services")

        if int(row["database_count"]) != 10:
            raise DomainManifestError(f"{row['domain']} does not own 10 databases")

        if int(row["table_count"]) != 100:
            raise DomainManifestError(f"{row['domain']} does not own 100 tables")

        cdc_tables = int(row["full_cdc_table_count"]) + int(
            row["excluded_cdc_table_count"]
        )

        if cdc_tables != 100:
            raise DomainManifestError(f"{row['domain']} has invalid CDC totals")

        effective_relationships = int(row["colocated_logical_reference_count"]) + int(
            row["event_driven_reference_count"]
        )

        if effective_relationships != int(row["outgoing_relationship_count"]):
            raise DomainManifestError(
                f"{row['domain']} has invalid relationship totals"
            )

        if row["frontend_exposure_policy"] != ("POLICY_PENDING"):
            raise DomainManifestError(
                f"{row['domain']} has an unexpected frontend policy"
            )

        if row["implementation_status"] != "PLANNED":
            raise DomainManifestError(f"{row['domain']} has an invalid status")


def _require_single_value(
    domain: str,
    rows: list[dict[str, str]],
    column: str,
) -> None:
    values = {row[column] for row in rows}

    if len(values) != 1:
        raise DomainManifestError(
            f"{domain} has inconsistent {column}: {sorted(values)}"
        )


def _read_csv(
    path: Path,
) -> list[dict[str, str]]:
    with path.open(
        newline="",
        encoding="utf-8",
    ) as stream:
        return list(DictReader(stream))
