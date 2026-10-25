"""Base interface for ecosystem manifest parsers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from agentmatch.models import ParsedManifest


class BaseManifestParser(ABC):
    """Abstract base class for all repository manifest parsers."""

    @abstractmethod
    def can_parse(self, filename: str) -> bool:
        """Check if this parser handles the given filename."""
        pass

    @abstractmethod
    def parse(self, content: str, filename: str) -> ParsedManifest:
        """Parse manifest content into a structured ParsedManifest object."""
        pass
