"""Core data models for AgentMatch AI."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ParsedManifest(BaseModel):
    """Normalized manifest extraction result from a single configuration file."""

    manifest_path: str
    language: str
    ecosystem: str  # e.g., 'python', 'node', 'java', 'go'
    dependencies: dict[str, str] = Field(default_factory=dict)
    dev_dependencies: dict[str, str] = Field(default_factory=dict)
    frameworks: list[str] = Field(default_factory=list)
    test_frameworks: list[str] = Field(default_factory=list)
    linters_and_formatters: list[str] = Field(default_factory=list)
    build_tools: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TechStackProfile(BaseModel):
    """Unified technology profile aggregated across all repository manifests."""

    repo_name: str
    repo_url: str | None = None
    primary_language: str | None = None
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    dependencies: dict[str, str] = Field(default_factory=dict)
    dev_dependencies: dict[str, str] = Field(default_factory=dict)
    test_frameworks: list[str] = Field(default_factory=list)
    build_tools: list[str] = Field(default_factory=list)
    linters_and_formatters: list[str] = Field(default_factory=list)
    ci_cd: list[str] = Field(default_factory=list)
    manifests_found: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)

    def summary(self) -> str:
        """Return a compact human-readable summary of the stack."""
        langs = ", ".join(self.languages) or "Unknown"
        fws = ", ".join(self.frameworks) or "None detected"
        tests = ", ".join(self.test_frameworks) or "None detected"
        linters = ", ".join(self.linters_and_formatters) or "None detected"
        return (
            f"Repository: {self.repo_name}\n"
            f"Languages: {langs}\n"
            f"Frameworks: {fws}\n"
            f"Test Frameworks: {tests}\n"
            f"Linters/Formatters: {linters}\n"
            f"Total Dependencies: {len(self.dependencies) + len(self.dev_dependencies)}"
        )
