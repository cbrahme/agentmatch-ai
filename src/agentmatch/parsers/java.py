"""Java and JVM manifest parser for pom.xml and build.gradle."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from agentmatch.models import ParsedManifest
from agentmatch.parsers.base import BaseManifestParser

FRAMEWORK_PATTERNS = [
    (r"spring-boot", "Spring Boot"),
    (r"org\.springframework", "Spring Framework"),
    (r"quarkus", "Quarkus"),
    (r"micronaut", "Micronaut"),
    (r"dropwizard", "Dropwizard"),
    (r"hibernate", "Hibernate"),
    (r"jakarta\.persistence", "JPA"),
]

TEST_PATTERNS = [
    (r"junit", "JUnit"),
    (r"testng", "TestNG"),
    (r"mockito", "Mockito"),
    (r"assertj", "AssertJ"),
    (r"archunit", "ArchUnit"),
]

LINTER_PATTERNS = [
    (r"checkstyle", "Checkstyle"),
    (r"spotbugs", "SpotBugs"),
    (r"pmd", "PMD"),
    (r"sonarqube|sonar-maven", "SonarQube"),
    (r"spotless", "Spotless"),
]


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


class JavaManifestParser(BaseManifestParser):
    """Parser for Java Maven (pom.xml) and Gradle manifests."""

    def can_parse(self, filename: str) -> bool:
        name = Path(filename).name
        return name in ("pom.xml", "build.gradle", "build.gradle.kts")

    def parse(self, content: str, filename: str) -> ParsedManifest:
        name = Path(filename).name
        deps: dict[str, str] = {}
        dev_deps: dict[str, str] = {}
        build_tools: list[str] = []

        if name == "pom.xml":
            build_tools.append("Maven")
            try:
                root = ET.fromstring(content)
                for dep in root.iter():
                    if _strip_ns(dep.tag) == "dependency":
                        group_id = ""
                        artifact_id = ""
                        version = "*"
                        scope = "compile"
                        for child in dep:
                            child_tag = _strip_ns(child.tag)
                            child_text = (child.text or "").strip()
                            if child_tag == "groupId":
                                group_id = child_text
                            elif child_tag == "artifactId":
                                artifact_id = child_text
                            elif child_tag == "version":
                                version = child_text
                            elif child_tag == "scope":
                                scope = child_text.lower()

                        if artifact_id:
                            full_coord = f"{group_id}:{artifact_id}" if group_id else artifact_id
                            if scope in ("test", "provided"):
                                dev_deps[full_coord] = version
                            else:
                                deps[full_coord] = version
            except ET.ParseError:
                pass

        elif name in ("build.gradle", "build.gradle.kts"):
            build_tools.append("Gradle")
            # Parse gradle dependency lines: implementation 'group:artifact:version' or ("...")
            dep_pattern = re.compile(
                r"""(implementation|testImplementation|testCompile|compileOnly|api)\s*\(?['"]([^'"]+)['"]\)?"""
            )
            for line in content.splitlines():
                m = dep_pattern.search(line)
                if m:
                    scope, coord = m.group(1), m.group(2)
                    parts = coord.split(":")
                    pkg = f"{parts[0]}:{parts[1]}" if len(parts) >= 2 else coord
                    ver = parts[2] if len(parts) >= 3 else "*"
                    if "test" in scope.lower():
                        dev_deps[pkg] = ver
                    else:
                        deps[pkg] = ver

        all_keys = list(deps.keys()) + list(dev_deps.keys()) + [content]
        all_text = " ".join(all_keys).lower()

        frameworks = [name for pat, name in FRAMEWORK_PATTERNS if re.search(pat, all_text)]
        test_frameworks = [name for pat, name in TEST_PATTERNS if re.search(pat, all_text)]
        linters = [name for pat, name in LINTER_PATTERNS if re.search(pat, all_text)]

        return ParsedManifest(
            manifest_path=filename,
            language="Java",
            ecosystem="java",
            dependencies=deps,
            dev_dependencies=dev_deps,
            frameworks=sorted(list(set(frameworks))),
            test_frameworks=sorted(list(set(test_frameworks))),
            linters_and_formatters=sorted(list(set(linters))),
            build_tools=sorted(list(set(build_tools))),
            metadata={},
        )
