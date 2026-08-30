"""Enterprise application architecture."""

from retail_intelligence_platform.architecture.domains import (
    DOMAIN_MANIFEST_COLUMNS,
    DomainManifestError,
    DomainManifestSummary,
    validate_domain_manifest,
    write_domain_manifest,
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
    "DOMAIN_MANIFEST_COLUMNS",
    "MANIFEST_COLUMNS",
    "RELATIONSHIP_MANIFEST_COLUMNS",
    "SERVICE_MANIFEST_COLUMNS",
    "ArchitectureSummary",
    "ArchitectureValidationError",
    "CdcMode",
    "DomainManifestError",
    "DomainManifestSummary",
    "PolicySummary",
    "RelationshipManifestError",
    "RelationshipManifestSummary",
    "TablePolicy",
    "load_table_policies",
    "summarize_table_policies",
    "validate_architecture",
    "validate_domain_manifest",
    "validate_implementation_manifest",
    "validate_relationship_manifest",
    "validate_service_manifest",
    "validate_table_policies",
    "write_domain_manifest",
    "write_implementation_manifest",
    "write_relationship_manifest",
    "write_service_manifest",
]
