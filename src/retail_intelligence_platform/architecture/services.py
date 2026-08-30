"""Generation of the enterprise microservice manifest."""

from collections import defaultdict
from csv import DictReader, DictWriter
from pathlib import Path

SERVICE_MANIFEST_COLUMNS = (
    "lesson_number",
    "domain_id",
    "domain",
    "service_group",
    "microservice_id",
    "microservice_name",
    "team_id",
    "db_cluster_count",
    "db_clusters",
    "database_name",
    "schema_name",
    "owned_table_count",
    "owned_tables",
    "full_cdc_table_count",
    "excluded_cdc_table_count",
    "backend_module_path",
    "api_base_path",
    "docker_profile",
    "deployment_unit",
    "frontend_integration",
    "implementation_status",
)


def write_service_manifest(
    table_manifest_path: Path,
    destination_path: Path,
) -> int:
    """Generate one service definition per microservice."""

    with table_manifest_path.open(
        encoding="utf-8",
        newline="",
    ) as source:
        table_rows = list(DictReader(source))

    grouped: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in table_rows:
        grouped[row["microservice_id"]].append(row)

    service_rows = []

    for microservice_id, owned_tables in grouped.items():
        owned_tables.sort(key=lambda row: row["full_table_name"])

        first = owned_tables[0]

        _validate_service_invariants(
            microservice_id,
            owned_tables,
        )

        full_cdc = sum(row["effective_cdc_mode"] == "FULL" for row in owned_tables)
        excluded_cdc = sum(
            row["effective_cdc_mode"] == "EXCLUDED" for row in owned_tables
        )

        domain = first["domain"]
        service_name = first["microservice_name"]
        service_sequence = service_name.rsplit(
            "-",
            maxsplit=1,
        )[-1]

        clusters = sorted({row["db_cluster"] for row in owned_tables})

        service_rows.append(
            {
                "lesson_number": first["lesson_number"],
                "domain_id": first["domain_id"],
                "domain": domain,
                "service_group": first["service_group"],
                "microservice_id": microservice_id,
                "microservice_name": service_name,
                "team_id": first["team_id"],
                "db_cluster_count": str(len(clusters)),
                "db_clusters": "|".join(clusters),
                "database_name": first["database_name"],
                "schema_name": first["schema_name"],
                "owned_table_count": str(len(owned_tables)),
                "owned_tables": "|".join(
                    row["full_table_name"] for row in owned_tables
                ),
                "full_cdc_table_count": str(full_cdc),
                "excluded_cdc_table_count": str(excluded_cdc),
                "backend_module_path": (
                    f"applications/backend/services/{domain}/{service_name}"
                ),
                "api_base_path": (f"/api/v1/{domain}/{service_sequence}"),
                "docker_profile": (f"domain-{domain}"),
                "deployment_unit": service_name,
                "frontend_integration": ("DOMAIN_POLICY_PENDING"),
                "implementation_status": "PLANNED",
            }
        )

    service_rows.sort(key=lambda row: int(row["microservice_id"].removeprefix("svc-")))

    destination_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with destination_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as destination:
        writer = DictWriter(
            destination,
            fieldnames=SERVICE_MANIFEST_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(service_rows)

    return len(service_rows)


def validate_service_manifest(
    manifest_path: Path,
) -> None:
    """Validate microservice ownership and lesson coverage."""

    with manifest_path.open(
        encoding="utf-8",
        newline="",
    ) as source:
        reader = DictReader(source)
        rows = list(reader)
        columns = tuple(reader.fieldnames or ())

    if columns != SERVICE_MANIFEST_COLUMNS:
        raise ValueError("Unexpected service manifest columns")

    if len(rows) != 1_000:
        raise ValueError(f"Expected 1000 services, found {len(rows)}")

    service_ids = {row["microservice_id"] for row in rows}
    databases = {row["database_name"] for row in rows}
    api_paths = {row["api_base_path"] for row in rows}
    module_paths = {row["backend_module_path"] for row in rows}

    for label, values in (
        ("service identifiers", service_ids),
        ("database names", databases),
        ("API paths", api_paths),
        ("backend module paths", module_paths),
    ):
        if len(values) != 1_000:
            raise ValueError(f"Expected 1000 unique {label}, found {len(values)}")

    lesson_numbers = {int(row["lesson_number"]) for row in rows}

    if lesson_numbers != set(range(201, 1_201)):
        raise ValueError("Service lessons do not cover 201 through 1200")

    owned_tables: set[str] = set()

    for row in rows:
        if int(row["owned_table_count"]) != 10:
            raise ValueError(
                f"Service does not own ten tables: {row['microservice_id']}"
            )
        if int(row["db_cluster_count"]) < 1:
            raise ValueError(
                f"Service has no database clusters: {row['microservice_id']}"
            )

        clusters = row["db_clusters"].split("|")

        if not row["db_clusters"] or any(not cluster for cluster in clusters):
            raise ValueError(
                f"Service has invalid database clusters: {row['microservice_id']}"
            )

        if len(clusters) != int(row["db_cluster_count"]):
            raise ValueError(
                "Database cluster count does not match "
                f"cluster list for {row['microservice_id']}"
            )

        if clusters != sorted(set(clusters)):
            raise ValueError(
                f"Database clusters are not deterministic for {row['microservice_id']}"
            )

        tables = row["owned_tables"].split("|")

        if len(tables) != 10:
            raise ValueError(f"Invalid owned-table list for {row['microservice_id']}")

        overlap = owned_tables.intersection(tables)

        if overlap:
            raise ValueError(f"Tables assigned to multiple services: {sorted(overlap)}")

        owned_tables.update(tables)

        cdc_total = int(row["full_cdc_table_count"]) + int(
            row["excluded_cdc_table_count"]
        )

        if cdc_total != 10:
            raise ValueError(
                "CDC classification does not cover "
                f"all tables for "
                f"{row['microservice_id']}"
            )

    if len(owned_tables) != 10_000:
        raise ValueError("Service manifest does not account for all 10000 tables")


def _validate_service_invariants(
    microservice_id: str,
    rows: list[dict[str, str]],
) -> None:
    if len(rows) != 10:
        raise ValueError(f"{microservice_id} owns {len(rows)} tables instead of 10")

    invariant_columns = (
        "lesson_number",
        "domain_id",
        "domain",
        "service_group",
        "microservice_name",
        "team_id",
        "database_name",
        "schema_name",
    )

    for column in invariant_columns:
        values = {row[column] for row in rows}

        if len(values) != 1:
            raise ValueError(
                f"{microservice_id} has inconsistent {column}: {sorted(values)}"
            )
