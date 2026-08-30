"""Enterprise application architecture."""

from retail_intelligence_platform.architecture.registry import (
    ArchitectureSummary,
    ArchitectureValidationError,
    validate_architecture,
)

__all__ = [
    "ArchitectureSummary",
    "ArchitectureValidationError",
    "validate_architecture",
]
