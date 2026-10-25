"""Registry and dispatcher for ecosystem manifest parsers."""
from __future__ import annotations

from pathlib import Path
from agentmatch.models import ParsedManifest
from agentmatch.parsers.base import BaseManifestParser
from agentmatch.parsers.go import GoManifestParser
from agentmatch.parsers.java import JavaManifestParser
from agentmatch.parsers.node import NodeManifestParser
from agentmatch.parsers.python import PythonManifestParser

PARSERS: list[BaseManifestParser] = [
    PythonManifestParser(),
    NodeManifestParser(),
    JavaManifestParser(),
    GoManifestParser(),
]


def parse_manifest_content(content: str, filename: str) -> ParsedManifest | None:
    """Find a matching parser and parse the manifest content."""
    for parser in PARSERS:
        if parser.can_parse(filename):
            return parser.parse(content, filename)
    return None


def can_parse_file(filename: str) -> bool:
    """Check if any registered parser can handle this filename."""
    return any(parser.can_parse(filename) for parser in PARSERS)


__all__ = [
    "BaseManifestParser",
    "PythonManifestParser",
    "NodeManifestParser",
    "JavaManifestParser",
    "GoManifestParser",
    "parse_manifest_content",
    "can_parse_file",
    "PARSERS",
]
