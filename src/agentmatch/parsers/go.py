"""Go ecosystem manifest parser for go.mod."""
from __future__ import annotations

import re
from pathlib import Path
from agentmatch.models import ParsedManifest
from agentmatch.parsers.base import BaseManifestParser

FRAMEWORK_MAP = {
    "github.com/gin-gonic/gin": "Gin",
    "github.com/labstack/echo": "Echo",
    "github.com/gofiber/fiber": "Fiber",
    "github.com/go-chi/chi": "Chi",
    "google.golang.org/grpc": "gRPC",
}

TEST_MAP = {
    "github.com/stretchr/testify": "Testify",
    "github.com/onsi/ginkgo": "Ginkgo",
    "github.com/onsi/gomega": "Gomega",
}

LINTER_MAP = {
    "golangci-lint": "golangci-lint",
    "staticcheck": "staticcheck",
    "revive": "revive",
}


class GoManifestParser(BaseManifestParser):
    """Parser for Go go.mod manifests."""

    def can_parse(self, filename: str) -> bool:
        return Path(filename).name == "go.mod"

    def parse(self, content: str, filename: str) -> ParsedManifest:
        deps: dict[str, str] = {}
        dev_deps: dict[str, str] = {}
        metadata: dict[str, str] = {}

        in_require_block = False
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("//"):
                continue

            if line.startswith("module "):
                metadata["module"] = line.split("module ", 1)[1].strip()
                continue
            if line.startswith("go "):
                metadata["go_version"] = line.split("go ", 1)[1].strip()
                continue

            if line.startswith("require ("):
                in_require_block = True
                continue
            elif in_require_block and line == ")":
                in_require_block = False
                continue

            target_line = ""
            if in_require_block:
                target_line = line
            elif line.startswith("require "):
                target_line = line.split("require ", 1)[1].strip()

            if target_line:
                is_indirect = "// indirect" in target_line
                clean_dep = target_line.split("//", 1)[0].strip()
                parts = clean_dep.split()
                if len(parts) >= 2:
                    mod_path, ver = parts[0], parts[1]
                    if is_indirect:
                        dev_deps[mod_path] = ver
                    else:
                        deps[mod_path] = ver

        all_deps = {**deps, **dev_deps}
        frameworks = [v for k, v in FRAMEWORK_MAP.items() if any(k in dep for dep in all_deps)]
        test_frameworks = [v for k, v in TEST_MAP.items() if any(k in dep for dep in all_deps)]
        linters = [v for k, v in LINTER_MAP.items() if any(k in dep for dep in all_deps)]

        return ParsedManifest(
            manifest_path=filename,
            language="Go",
            ecosystem="go",
            dependencies=deps,
            dev_dependencies=dev_deps,
            frameworks=sorted(list(set(frameworks))),
            test_frameworks=sorted(list(set(test_frameworks))),
            linters_and_formatters=sorted(list(set(linters))),
            build_tools=["Go Modules"],
            metadata=metadata,
        )
