"""Enterprise application architecture."""

from retail_intelligence_platform.architecture.backend import (
    BACKEND_CONTRACT_COLUMNS,
    GRADLE_VERSION,
    JAVA_VERSION,
    SPRING_BOOT_VERSION,
    BackendContractError,
    BackendContractSummary,
    validate_backend_contract_manifest,
    write_backend_contract_manifest,
)
from retail_intelligence_platform.architecture.domains import (
    DOMAIN_MANIFEST_COLUMNS,
    DomainManifestError,
    DomainManifestSummary,
    validate_domain_manifest,
    write_domain_manifest,
)
from retail_intelligence_platform.architecture.frontend import (
    ADMIN_ONLY_DOMAINS,
    CUSTOMER_AND_ADMIN_DOMAINS,
    CUSTOMER_ONLY_DOMAINS,
    FRONTEND_POLICY_COLUMNS,
    INTERNAL_ONLY_DOMAINS,
    FrontendPolicyError,
    FrontendPolicySummary,
    validate_frontend_policy_manifest,
    write_frontend_policy_manifest,
)
from retail_intelligence_platform.architecture.manifest import (
    MANIFEST_COLUMNS,
    validate_implementation_manifest,
    write_implementation_manifest,
)
from retail_intelligence_platform.architecture.policy import (
    CdcMode,
    PolicySummary,
    TablePolicy,
    load_table_policies,
    summarize_table_policies,
    validate_table_policies,
)
from retail_intelligence_platform.architecture.registry import (
    ArchitectureSummary,
    ArchitectureValidationError,
    validate_architecture,
)
from retail_intelligence_platform.architecture.relationships import (
    RELATIONSHIP_MANIFEST_COLUMNS,
    RelationshipManifestError,
    RelationshipManifestSummary,
    validate_relationship_manifest,
    write_relationship_manifest,
)
from retail_intelligence_platform.architecture.services import (
    SERVICE_MANIFEST_COLUMNS,
    validate_service_manifest,
    write_service_manifest,
)

__all__ = [
    "ADMIN_ONLY_DOMAINS",
    "BACKEND_CONTRACT_COLUMNS",
    "CUSTOMER_AND_ADMIN_DOMAINS",
    "CUSTOMER_ONLY_DOMAINS",
    "DOMAIN_MANIFEST_COLUMNS",
    "FRONTEND_POLICY_COLUMNS",
    "GRADLE_VERSION",
    "INTERNAL_ONLY_DOMAINS",
    "JAVA_VERSION",
    "MANIFEST_COLUMNS",
    "RELATIONSHIP_MANIFEST_COLUMNS",
    "SERVICE_MANIFEST_COLUMNS",
    "SPRING_BOOT_VERSION",
    "ArchitectureSummary",
    "ArchitectureValidationError",
    "BackendContractError",
    "BackendContractSummary",
    "CdcMode",
    "DomainManifestError",
    "DomainManifestSummary",
    "FrontendPolicyError",
    "FrontendPolicySummary",
    "PolicySummary",
    "RelationshipManifestError",
    "RelationshipManifestSummary",
    "TablePolicy",
    "load_table_policies",
    "summarize_table_policies",
    "validate_architecture",
    "validate_backend_contract_manifest",
    "validate_domain_manifest",
    "validate_frontend_policy_manifest",
    "validate_implementation_manifest",
    "validate_relationship_manifest",
    "validate_service_manifest",
    "validate_table_policies",
    "write_backend_contract_manifest",
    "write_domain_manifest",
    "write_frontend_policy_manifest",
    "write_implementation_manifest",
    "write_relationship_manifest",
    "write_service_manifest",
]
