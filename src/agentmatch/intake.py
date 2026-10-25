"""Repository intake and manifest aggregator."""
from __future__ import annotations

import os
import re
from pathlib import Path
import httpx
from agentmatch.models import ParsedManifest, TechStackProfile
from agentmatch.parsers import can_parse_file, parse_manifest_content

IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "target",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
}

COMMON_MANIFEST_PATHS = [
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "pom.xml",
    "build.gradle",
    "go.mod",
    ".github/workflows/ci.yml",
    ".github/workflows/main.yml",
]


class RepoIntakeAgent:
    """Agent responsible for ingesting local or remote repository manifests."""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def inspect_local_dir(self, directory: str | Path) -> TechStackProfile:
        """Scan a local directory for manifests and build a TechStackProfile."""
        dir_path = Path(directory).resolve()
        repo_name = dir_path.name
        parsed_manifests: list[ParsedManifest] = []
        ci_cd: list[str] = []

        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for file in files:
                rel_path = str(Path(root, file).relative_to(dir_path))
                if can_parse_file(file):
                    full_path = Path(root, file)
                    try:
                        content = full_path.read_text(encoding="utf-8", errors="ignore")
                        manifest = parse_manifest_content(content, rel_path)
                        if manifest:
                            parsed_manifests.append(manifest)
                    except Exception:
                        continue

                # Check for GitHub Actions CI/CD
                if ".github/workflows" in rel_path and (file.endswith(".yml") or file.endswith(".yaml")):
                    if "GitHub Actions" not in ci_cd:
                        ci_cd.append("GitHub Actions")

        return self._build_profile(repo_name=repo_name, manifests=parsed_manifests, ci_cd=ci_cd)

    def fetch_github_repo(self, repo_url: str) -> TechStackProfile:
        """Fetch manifest files from a public GitHub repository."""
        clean_url = repo_url.rstrip("/")
        match = re.match(r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", clean_url)
        if not match:
            raise ValueError(f"Invalid GitHub repository URL: {repo_url}")

        owner, repo = match.group(1), match.group(2)
        parsed_manifests: list[ParsedManifest] = []
        ci_cd: list[str] = []

        headers = {"User-Agent": "AgentMatch-AI"}
        client = httpx.Client(timeout=self.timeout, headers=headers, follow_redirects=True)

        try:
            for manifest_file in COMMON_MANIFEST_PATHS:
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{manifest_file}"
                response = client.get(raw_url)
                if response.status_code == 200:
                    content = response.text
                    if ".github/workflows" in manifest_file:
                        if "GitHub Actions" not in ci_cd:
                            ci_cd.append("GitHub Actions")
                    elif can_parse_file(manifest_file):
                        manifest = parse_manifest_content(content, manifest_file)
                        if manifest:
                            parsed_manifests.append(manifest)
        finally:
            client.close()

        return self._build_profile(
            repo_name=repo,
            repo_url=repo_url,
            manifests=parsed_manifests,
            ci_cd=ci_cd,
        )

    def _build_profile(
        self,
        repo_name: str,
        manifests: list[ParsedManifest],
        ci_cd: list[str],
        repo_url: str | None = None,
    ) -> TechStackProfile:
        """Consolidate parsed manifests into a TechStackProfile."""
        languages: list[str] = []
        frameworks: list[str] = []
        dependencies: dict[str, str] = {}
        dev_dependencies: dict[str, str] = {}
        test_frameworks: list[str] = []
        build_tools: list[str] = []
        linters: list[str] = []
        manifests_found: list[str] = []

        for m in manifests:
            manifests_found.append(m.manifest_path)
            if m.language not in languages:
                languages.append(m.language)
            for f in m.frameworks:
                if f not in frameworks:
                    frameworks.append(f)
            for t in m.test_frameworks:
                if t not in test_frameworks:
                    test_frameworks.append(t)
            for l_ in m.linters_and_formatters:
                if l_ not in linters:
                    linters.append(l_)
            for b in m.build_tools:
                if b not in build_tools:
                    build_tools.append(b)

            dependencies.update(m.dependencies)
            dev_dependencies.update(m.dev_dependencies)

        primary_language = languages[0] if languages else None

        # Detect gaps / missing capabilities
        missing_caps: list[str] = []
        if not test_frameworks:
            missing_caps.append("test_coverage")
        if not linters:
            missing_caps.append("linting_formatting")
        if not ci_cd:
            missing_caps.append("ci_cd_automation")

        return TechStackProfile(
            repo_name=repo_name,
            repo_url=repo_url,
            primary_language=primary_language,
            languages=languages,
            frameworks=sorted(frameworks),
            dependencies=dependencies,
            dev_dependencies=dev_dependencies,
            test_frameworks=sorted(test_frameworks),
            build_tools=sorted(build_tools),
            linters_and_formatters=sorted(linters),
            ci_cd=sorted(ci_cd),
            manifests_found=sorted(manifests_found),
            missing_capabilities=sorted(missing_caps),
        )
