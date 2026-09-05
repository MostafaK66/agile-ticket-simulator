"""Domain-specific errors."""


class AgileSimulatorError(Exception):
    """Base exception for expected application failures."""


class ConfigurationError(AgileSimulatorError):
    """Configuration is missing, malformed, or invalid."""


class SimulationError(AgileSimulatorError):
    """Ticket generation cannot produce valid output."""


class DataValidationError(AgileSimulatorError):
    """Tabular data does not satisfy the application schema."""


class ForecastError(AgileSimulatorError):
    """Daily metrics cannot support the configured forecast."""


class ArtifactError(AgileSimulatorError):
    """Output artifacts cannot be written."""
