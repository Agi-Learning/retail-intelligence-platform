"""Deterministic frontend exposure policies for enterprise domains."""

from collections import Counter
from csv import DictReader, DictWriter
from dataclasses import dataclass
from pathlib import Path
from typing import cast

EXPECTED_DOMAINS = 100

CUSTOMER_AND_ADMIN_DOMAINS = frozenset(
    {
        "cart",
        "catalog",
        "checkout",
        "content",
        "currency",
        "customer",
        "delivery",
        "digital_goods",
        "engagement",
        "gift_card",
        "identity",
        "international",
        "inventory",
        "localization",
        "loyalty",
        "marketplace",
        "membership",
        "order",
        "payment",
        "pricing",
        "product",
        "promotion",
        "refund",
        "returns",
        "reviews",
        "search",
        "shipping",
        "store",
        "subscription",
        "support",
    }
)

CUSTOMER_ONLY_DOMAINS = frozenset(
    {
        "mobile",
        "personalization",
        "recommendation",
        "social",
        "web",
    }
)

ADMIN_ONLY_DOMAINS = frozenset(
    {
        "accounting",
        "advertising",
        "affiliate",
        "analytics",
        "audit",
        "b2b",
        "commission",
        "compliance",
        "crm",
        "demand",
        "dropship",
        "exchange",
        "experimentation",
        "finance",
        "forecasting",
        "fraud",
        "fulfillment",
        "geo",
        "last_mile",
        "legal",
        "listing",
        "logistics",
        "marketing",
        "operations",
        "payout",
        "planning",
        "pos",
        "privacy",
        "procurement",
        "quality",
        "reference",
        "reverse_logistics",
        "risk",
        "seller",
        "settlement",
        "supplier",
        "supply_chain",
        "sustainability",
        "tax",
        "transport",
        "vendor_management",
        "warehouse",
        "wholesale",
    }
)

INTERNAL_ONLY_DOMAINS = frozenset(
    {
        "cdc",
        "data_platform",
        "data_quality",
        "email",
        "etl",
        "feature_store",
        "governance",
        "iam",
        "integration",
        "lakehouse",
        "master_data",
        "messaging",
        "metadata",
        "ml",
        "notification",
        "observability",
        "outbox",
        "platform",
        "push",
        "security",
        "sms",
        "streaming",
    }
)

SUPPORTED_DOMAINS = (
    CUSTOMER_AND_ADMIN_DOMAINS
    | CUSTOMER_ONLY_DOMAINS
    | ADMIN_ONLY_DOMAINS
    | INTERNAL_ONLY_DOMAINS
)

FRONTEND_POLICY_COLUMNS = (
    "lesson_number",
    "domain_id",
    "domain",
    "exposure_policy",
    "customer_web_enabled",
    "admin_web_enabled",
    "customer_frontend_path",
    "admin_frontend_path",
    "customer_route",
    "admin_route",
    "api_gateway_base_path",
    "api_access_policy",
    "customer_auth_audience",
    "admin_auth_audience",
    "backend_domain_path",
    "docker_profile",
    "deployment_namespace",
    "implementation_status",
)


class FrontendPolicyError(ValueError):
    """Raised when frontend exposure policy is incomplete."""


@dataclass(frozen=True, slots=True)
class FrontendPolicySummary:
    """Validated frontend-policy measurements."""

    domains: int
    customer_and_admin: int
    customer_only: int
    admin_only: int
    internal_only: int
    customer_web_domains: int
    admin_web_domains: int
    public_api_domains: int
    internal_api_domains: int


def write_frontend_policy_manifest(
    domain_manifest_path: Path,
    destination: Path,
) -> int:
    """Write React and API exposure decisions for every domain."""

    with domain_manifest_path.open(
        newline="",
        encoding="utf-8",
    ) as stream:
        domains = list(DictReader(stream))

    if len(domains) != EXPECTED_DOMAINS:
        raise FrontendPolicyError(
            f"Expected {EXPECTED_DOMAINS} domains, found {len(domains)}"
        )

    actual_domains = {row["domain"] for row in domains}

    if actual_domains != SUPPORTED_DOMAINS:
        missing = sorted(SUPPORTED_DOMAINS - actual_domains)
        unexpected = sorted(actual_domains - SUPPORTED_DOMAINS)

        raise FrontendPolicyError(
            f"Domain policy mismatch; missing={missing}, unexpected={unexpected}"
        )

    rows = [
        _build_policy_row(domain)
        for domain in sorted(
            domains,
            key=lambda row: row["domain"],
        )
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
            fieldnames=FRONTEND_POLICY_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(cast(list, rows))

    return len(rows)


def validate_frontend_policy_manifest(
    path: Path,
) -> FrontendPolicySummary:
    """Validate frontend and API exposure coverage."""

    with path.open(
        newline="",
        encoding="utf-8",
    ) as stream:
        reader = DictReader(stream)
        rows = list(reader)
        columns = tuple(reader.fieldnames or ())

    if columns != FRONTEND_POLICY_COLUMNS:
        raise FrontendPolicyError("Unexpected frontend policy columns")

    if len(rows) != EXPECTED_DOMAINS:
        raise FrontendPolicyError(
            f"Expected {EXPECTED_DOMAINS} policies, found {len(rows)}"
        )

    domains = {row["domain"] for row in rows}

    if domains != SUPPORTED_DOMAINS:
        raise FrontendPolicyError("Frontend policies do not cover all domains")

    policies = Counter(row["exposure_policy"] for row in rows)

    expected_policies = {
        "CUSTOMER_AND_ADMIN": 30,
        "CUSTOMER_ONLY": 5,
        "ADMIN_ONLY": 43,
        "INTERNAL_ONLY": 22,
    }

    if dict(policies) != expected_policies:
        raise FrontendPolicyError(f"Unexpected policy distribution: {dict(policies)}")

    _validate_rows(rows)

    customer_web_domains = sum(row["customer_web_enabled"] == "Y" for row in rows)

    admin_web_domains = sum(row["admin_web_enabled"] == "Y" for row in rows)

    public_api_domains = sum(
        row["api_access_policy"] == "PUBLIC_AUTHENTICATED" for row in rows
    )

    internal_api_domains = sum(
        row["api_access_policy"] == "INTERNAL_AUTHORIZED" for row in rows
    )

    return FrontendPolicySummary(
        domains=len(rows),
        customer_and_admin=policies["CUSTOMER_AND_ADMIN"],
        customer_only=policies["CUSTOMER_ONLY"],
        admin_only=policies["ADMIN_ONLY"],
        internal_only=policies["INTERNAL_ONLY"],
        customer_web_domains=customer_web_domains,
        admin_web_domains=admin_web_domains,
        public_api_domains=public_api_domains,
        internal_api_domains=internal_api_domains,
    )


def _build_policy_row(
    domain: dict[str, str],
) -> dict[str, str]:
    name = domain["domain"]
    exposure_policy = _exposure_policy(name)

    customer_enabled = exposure_policy in {
        "CUSTOMER_AND_ADMIN",
        "CUSTOMER_ONLY",
    }

    admin_enabled = exposure_policy in {
        "CUSTOMER_AND_ADMIN",
        "ADMIN_ONLY",
    }

    api_access_policy = (
        "PUBLIC_AUTHENTICATED" if customer_enabled else "INTERNAL_AUTHORIZED"
    )

    return {
        "lesson_number": "128",
        "domain_id": domain["domain_id"],
        "domain": name,
        "exposure_policy": exposure_policy,
        "customer_web_enabled": ("Y" if customer_enabled else "N"),
        "admin_web_enabled": ("Y" if admin_enabled else "N"),
        "customer_frontend_path": (
            domain["customer_frontend_path"] if customer_enabled else ""
        ),
        "admin_frontend_path": (domain["admin_frontend_path"] if admin_enabled else ""),
        "customer_route": (f"/{name}" if customer_enabled else ""),
        "admin_route": (f"/admin/{name}" if admin_enabled else ""),
        "api_gateway_base_path": domain["api_gateway_base_path"],
        "api_access_policy": api_access_policy,
        "customer_auth_audience": ("retail-customer-web" if customer_enabled else ""),
        "admin_auth_audience": ("retail-admin-web" if admin_enabled else ""),
        "backend_domain_path": domain["backend_domain_path"],
        "docker_profile": domain["docker_profile"],
        "deployment_namespace": domain["deployment_namespace"],
        "implementation_status": "PLANNED",
    }


def _exposure_policy(
    domain: str,
) -> str:
    if domain in CUSTOMER_AND_ADMIN_DOMAINS:
        return "CUSTOMER_AND_ADMIN"

    if domain in CUSTOMER_ONLY_DOMAINS:
        return "CUSTOMER_ONLY"

    if domain in ADMIN_ONLY_DOMAINS:
        return "ADMIN_ONLY"

    if domain in INTERNAL_ONLY_DOMAINS:
        return "INTERNAL_ONLY"

    raise FrontendPolicyError(f"No frontend policy exists for {domain}")


def _validate_rows(
    rows: list[dict[str, str]],
) -> None:
    for row in rows:
        domain = row["domain"]
        policy = row["exposure_policy"]

        customer_enabled = row["customer_web_enabled"] == "Y"
        admin_enabled = row["admin_web_enabled"] == "Y"

        if row["lesson_number"] != "128":
            raise FrontendPolicyError(f"{domain} has an invalid lesson")

        if policy == "CUSTOMER_AND_ADMIN":
            if not customer_enabled or not admin_enabled:
                raise FrontendPolicyError(f"{domain} must enable both web apps")

        elif policy == "CUSTOMER_ONLY":
            if not customer_enabled or admin_enabled:
                raise FrontendPolicyError(f"{domain} has invalid customer-only routing")

        elif policy == "ADMIN_ONLY":
            if customer_enabled or not admin_enabled:
                raise FrontendPolicyError(f"{domain} has invalid admin-only routing")

        elif policy == "INTERNAL_ONLY":
            if customer_enabled or admin_enabled:
                raise FrontendPolicyError(f"{domain} must not expose browser routes")

        else:
            raise FrontendPolicyError(f"{domain} has an unknown policy")

        if customer_enabled:
            if (
                not row["customer_frontend_path"]
                or not row["customer_route"]
                or not row["customer_auth_audience"]
            ):
                raise FrontendPolicyError(f"{domain} has incomplete customer routing")
        elif (
            row["customer_frontend_path"]
            or row["customer_route"]
            or row["customer_auth_audience"]
        ):
            raise FrontendPolicyError(f"{domain} unexpectedly exposes customer routing")

        if admin_enabled:
            if (
                not row["admin_frontend_path"]
                or not row["admin_route"]
                or not row["admin_auth_audience"]
            ):
                raise FrontendPolicyError(f"{domain} has incomplete admin routing")
        elif (
            row["admin_frontend_path"]
            or row["admin_route"]
            or row["admin_auth_audience"]
        ):
            raise FrontendPolicyError(f"{domain} unexpectedly exposes admin routing")

        if row["implementation_status"] != "PLANNED":
            raise FrontendPolicyError(f"{domain} has an invalid implementation status")
