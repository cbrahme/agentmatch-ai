"""Python manifest parser for requirements.txt, pyproject.toml, and Pipfile."""
from __future__ import annotations

import re
import tomllib
from pathlib import Path
from agentmatch.models import ParsedManifest
from agentmatch.parsers.base import BaseManifestParser

FRAMEWORK_MAP = {
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "tornado": "Tornado",
    "litestar": "Litestar",
    "pyramid": "Pyramid",
    "sanic": "Sanic",
    "starlette": "Starlette",
}

TEST_MAP = {
    "pytest": "pytest",
    "pytest-asyncio": "pytest",
    "unittest": "unittest",
    "nose2": "nose2",
    "hypothesis": "hypothesis",
}

LINTER_MAP = {
    "ruff": "Ruff",
    "flake8": "Flake8",
    "black": "Black",
    "isort": "isort",
    "mypy": "mypy",
    "pylint": "Pylint",
    "bandit": "Bandit",
    "pyright": "Pyright",
}

BUILD_MAP = {
    "poetry": "Poetry",
    "hatch": "Hatch",
    "hatchling": "Hatch",
    "flit": "Flit",
    "pdm": "PDM",
    "setuptools": "setuptools",
    "pipenv": "Pipenv",
    "uv": "uv",
}


def _clean_req_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line or line.startswith("#") or line.startswith("-"):
        return None
    # Strip inline comments
    if " #" in line:
        line = line.split(" #", 1)[0].strip()
    # Strip environment markers
    if ";" in line:
        line = line.split(";", 1)[0].strip()
    # Strip extras like pydantic[email]
    match = re.match(r"^([a-zA-Z0-9_\-\.]+)(?:\[[^\]]+\])?(.*)$", line)
    if not match:
        return None
    pkg_name = match.group(1).lower().replace("_", "-")
    constraint = match.group(2).strip() or "*"
    return pkg_name, constraint


class PythonManifestParser(BaseManifestParser):
    """Parser for Python project manifests."""

    def can_parse(self, filename: str) -> bool:
        name = Path(filename).name
        return name in ("requirements.txt", "pyproject.toml", "Pipfile") or name.endswith("-requirements.txt")

    def parse(self, content: str, filename: str) -> ParsedManifest:
        name = Path(filename).name
        deps: dict[str, str] = {}
        dev_deps: dict[str, str] = {}
        metadata: dict[str, any] = {}

        if name.endswith("requirements.txt") or name == "requirements.txt":
            for line in content.splitlines():
                parsed = _clean_req_line(line)
                if parsed:
                    pkg, ver = parsed
                    if "test" in pkg or "pytest" in pkg or "lint" in pkg or "mypy" in pkg or "flake" in pkg:
                        dev_deps[pkg] = ver
                    else:
                        deps[pkg] = ver

        elif name == "pyproject.toml":
            data = tomllib.loads(content)
            # PEP 621 dependencies
            project = data.get("project", {})
            for req in project.get("dependencies", []):
                parsed = _clean_req_line(req)
                if parsed:
                    deps[parsed[0]] = parsed[1]

            # PEP 621 optional dependencies (e.g. dev, test)
            optional_deps = project.get("optional-dependencies", {})
            for group, req_list in optional_deps.items():
                for req in req_list:
                    parsed = _clean_req_line(req)
                    if parsed:
                        dev_deps[parsed[0]] = parsed[1]

            # Poetry dependencies
            poetry = data.get("tool", {}).get("poetry", {})
            for pkg, spec in poetry.get("dependencies", {}).items():
                if pkg.lower() != "python":
                    clean_name = pkg.lower().replace("_", "-")
                    ver = spec if isinstance(spec, str) else str(spec.get("version", "*"))
                    deps[clean_name] = ver

            for pkg, spec in poetry.get("dev-dependencies", {}).items():
                clean_name = pkg.lower().replace("_", "-")
                ver = spec if isinstance(spec, str) else str(spec.get("version", "*"))
                dev_deps[clean_name] = ver

            # Build system
            build_backend = data.get("build-system", {}).get("build-backend", "")
            if build_backend:
                metadata["build_backend"] = build_backend
                for b_key, b_val in BUILD_MAP.items():
                    if b_key in build_backend.lower():
                        metadata["build_tool"] = b_val

        all_deps = {**deps, **dev_deps}
        frameworks = [v for k, v in FRAMEWORK_MAP.items() if k in all_deps]
        test_frameworks = [v for k, v in TEST_MAP.items() if k in all_deps]
        linters = [v for k, v in LINTER_MAP.items() if k in all_deps]
        build_tools = [v for k, v in BUILD_MAP.items() if k in all_deps]
        if "build_tool" in metadata and metadata["build_tool"] not in build_tools:
            build_tools.append(metadata["build_tool"])

        return ParsedManifest(
            manifest_path=filename,
            language="Python",
            ecosystem="python",
            dependencies=deps,
            dev_dependencies=dev_deps,
            frameworks=sorted(list(set(frameworks))),
            test_frameworks=sorted(list(set(test_frameworks))),
            linters_and_formatters=sorted(list(set(linters))),
            build_tools=sorted(list(set(build_tools))),
            metadata=metadata,
        )
