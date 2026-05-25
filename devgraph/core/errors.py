"""Domain-specific exceptions."""


class DevGraphError(Exception):
    """Base exception for DevGraph errors."""


class ConfigError(DevGraphError):
    """Configuration file or value error."""


class GraphStoreError(DevGraphError):
    """Storage-layer error."""


class ExtractionError(DevGraphError):
    """Extractor failure."""

