"""Unit tests for ecosystem manifest parsers and RepoIntakeAgent."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
import httpx
import pytest
from agentmatch.intake import RepoIntakeAgent
from agentmatch.parsers.go import GoManifestParser
from agentmatch.parsers.java import JavaManifestParser
from agentmatch.parsers.node import NodeManifestParser
from agentmatch.parsers.python import PythonManifestParser

MOCK_PACKAGE_JSON_TS = """{
  "name": "my-next-app",
  "version": "1.0.0",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "test": "jest"
  },
  "dependencies": {
    "next": "14.2.0",
    "react": "18.3.0",
    "react-dom": "18.3.0"
  },
  "devDependencies": {
    "typescript": "^5.4.0",
    "@types/react": "^18.3.0",
    "jest": "^29.7.0",
    "eslint": "^8.57.0",
    "prettier": "^3.2.0"
  }
}"""

MOCK_PACKAGE_JSON_JS = """{
  "name": "express-api",
  "dependencies": {
    "express": "^4.19.0"
  },
  "devDependencies": {
    "mocha": "^10.0.0"
  }
}"""

MOCK_REQUIREMENTS_TXT = """# Core dependencies
fastapi==0.111.0
uvicorn[standard]>=0.29.0
pydantic>=2.7.0 # Data validation

# Testing and linting
pytest>=8.1.0
ruff>=0.4.0
"""

MOCK_PYPROJECT_TOML = """[project]
name = "flask-service"
version = "0.2.0"
dependencies = [
    "flask>=3.0.0",
    "requests==2.31.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "black>=24.0.0",
    "mypy>=1.9.0"
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""

MOCK_POM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>demo-service</artifactId>
    <version>0.0.1-SNAPSHOT</version>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
            <version>3.2.0</version>
        </dependency>
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <version>5.10.0</version>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-checkstyle-plugin</artifactId>
            <version>3.3.1</version>
        </dependency>
    </dependencies>
</project>
"""

MOCK_BUILD_GRADLE = """
plugins {
    id 'org.springframework.boot' version '3.2.0'
}
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa:3.2.0'
    testImplementation 'org.junit.jupiter:junit-jupiter:5.10.0'
}
"""

MOCK_GO_MOD = """module github.com/example/orders-service

go 1.22.0

require (
    github.com/gin-gonic/gin v1.9.1
    github.com/stretchr/testify v1.8.4
    golang.org/x/crypto v0.21.0 // indirect
)
"""


def test_node_manifest_typescript():
    parser = NodeManifestParser()
    assert parser.can_parse("package.json")
    manifest = parser.parse(MOCK_PACKAGE_JSON_TS, "package.json")

    assert manifest.language == "TypeScript"
    assert manifest.ecosystem == "node"
    assert "Next.js" in manifest.frameworks
    assert "React" in manifest.frameworks
    assert "Jest" in manifest.test_frameworks
    assert "ESLint" in manifest.linters_and_formatters
    assert "Prettier" in manifest.linters_and_formatters
    assert "next" in manifest.dependencies
    assert "typescript" in manifest.dev_dependencies


def test_node_manifest_javascript():
    parser = NodeManifestParser()
    manifest = parser.parse(MOCK_PACKAGE_JSON_JS, "package.json")
    assert manifest.language == "JavaScript"
    assert "Express" in manifest.frameworks
    assert "Mocha" in manifest.test_frameworks


def test_python_requirements_txt():
    parser = PythonManifestParser()
    assert parser.can_parse("requirements.txt")
    manifest = parser.parse(MOCK_REQUIREMENTS_TXT, "requirements.txt")

    assert manifest.language == "Python"
    assert "FastAPI" in manifest.frameworks
    assert "pytest" in manifest.test_frameworks
    assert "Ruff" in manifest.linters_and_formatters
    assert "fastapi" in manifest.dependencies
    assert "pytest" in manifest.dev_dependencies


def test_python_pyproject_toml():
    parser = PythonManifestParser()
    assert parser.can_parse("pyproject.toml")
    manifest = parser.parse(MOCK_PYPROJECT_TOML, "pyproject.toml")

    assert manifest.language == "Python"
    assert "Flask" in manifest.frameworks
    assert "pytest" in manifest.test_frameworks
    assert "Black" in manifest.linters_and_formatters
    assert "mypy" in manifest.linters_and_formatters
    assert "Hatch" in manifest.build_tools


def test_java_pom_xml():
    parser = JavaManifestParser()
    assert parser.can_parse("pom.xml")
    manifest = parser.parse(MOCK_POM_XML, "pom.xml")

    assert manifest.language == "Java"
    assert "Spring Boot" in manifest.frameworks
    assert "JUnit" in manifest.test_frameworks
    assert "Checkstyle" in manifest.linters_and_formatters
    assert "Maven" in manifest.build_tools
    assert "org.springframework.boot:spring-boot-starter-web" in manifest.dependencies
    assert "org.junit.jupiter:junit-jupiter" in manifest.dev_dependencies


def test_java_build_gradle():
    parser = JavaManifestParser()
    assert parser.can_parse("build.gradle")
    manifest = parser.parse(MOCK_BUILD_GRADLE, "build.gradle")

    assert manifest.language == "Java"
    assert "Spring Boot" in manifest.frameworks
    assert "JUnit" in manifest.test_frameworks
    assert "Gradle" in manifest.build_tools


def test_go_manifest():
    parser = GoManifestParser()
    assert parser.can_parse("go.mod")
    manifest = parser.parse(MOCK_GO_MOD, "go.mod")

    assert manifest.language == "Go"
    assert "Gin" in manifest.frameworks
    assert "Testify" in manifest.test_frameworks
    assert "github.com/gin-gonic/gin" in manifest.dependencies
    assert "golang.org/x/crypto" in manifest.dev_dependencies


def test_repo_intake_local_aggregation(tmp_path: Path):
    # Setup mock repo structure
    (tmp_path / "package.json").write_text(MOCK_PACKAGE_JSON_TS)
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: CI\non: [push]")

    agent = RepoIntakeAgent()
    profile = agent.inspect_local_dir(tmp_path)

    assert "TypeScript" in profile.languages
    assert "Next.js" in profile.frameworks
    assert "Jest" in profile.test_frameworks
    assert "GitHub Actions" in profile.ci_cd
    assert "package.json" in profile.manifests_found
    assert len(profile.missing_capabilities) == 0  # Has test, lint, and CI/CD


def test_repo_intake_fetch_github_repo_success():
    def mock_get(url, *args, **kwargs):
        mock_resp = MagicMock(spec=httpx.Response)
        url_str = str(url)
        if "package.json" in url_str:
            mock_resp.status_code = 200
            mock_resp.text = MOCK_PACKAGE_JSON_TS
        elif ".github/workflows/ci.yml" in url_str:
            mock_resp.status_code = 200
            mock_resp.text = "name: CI\non: [push]"
        else:
            mock_resp.status_code = 404
            mock_resp.text = "Not Found"
        return mock_resp

    with patch.object(httpx.Client, "get", side_effect=mock_get):
        agent = RepoIntakeAgent()
        profile = agent.fetch_github_repo("https://github.com/test-owner/sample-service")

        assert profile.repo_name == "sample-service"
        assert profile.repo_url == "https://github.com/test-owner/sample-service"
        assert "TypeScript" in profile.languages
        assert "Next.js" in profile.frameworks
        assert "Jest" in profile.test_frameworks
        assert "GitHub Actions" in profile.ci_cd
        assert "package.json" in profile.manifests_found


def test_repo_intake_fetch_github_repo_invalid_url():
    agent = RepoIntakeAgent()
    with pytest.raises(ValueError, match="Invalid GitHub repository URL"):
        agent.fetch_github_repo("https://gitlab.com/not/github")


def test_repo_intake_missing_capabilities(tmp_path: Path):
    # Only a bare package.json with no test runner or linters
    (tmp_path / "package.json").write_text('{"name": "bare-project"}')
    agent = RepoIntakeAgent()
    profile = agent.inspect_local_dir(tmp_path)

    assert "test_coverage" in profile.missing_capabilities
    assert "linting_formatting" in profile.missing_capabilities
    assert "ci_cd_automation" in profile.missing_capabilities


def test_python_poetry_pyproject():
    content = """
[tool.poetry]
name = "poetry-app"
version = "0.1.0"

[tool.poetry.dependencies]
python = "^3.11"
django = "^5.0.0"

[tool.poetry.dev-dependencies]
pytest = "^8.0.0"
ruff = "^0.4.0"
"""
    parser = PythonManifestParser()
    manifest = parser.parse(content, "pyproject.toml")
    assert manifest.language == "Python"
    assert "Django" in manifest.frameworks
    assert "pytest" in manifest.test_frameworks
    assert "Ruff" in manifest.linters_and_formatters
    assert "django" in manifest.dependencies
    assert "pytest" in manifest.dev_dependencies


def test_tech_stack_profile_summary():
    agent = RepoIntakeAgent()
    profile = agent._build_profile(
        repo_name="demo-app",
        manifests=[],
        ci_cd=[],
    )
    summary_text = profile.summary()
    assert "Repository: demo-app" in summary_text
    assert "Total Dependencies: 0" in summary_text

