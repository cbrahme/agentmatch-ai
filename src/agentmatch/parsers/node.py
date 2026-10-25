"""Node.js and TypeScript manifest parser for package.json."""
from __future__ import annotations

import json
from pathlib import Path
from agentmatch.models import ParsedManifest
from agentmatch.parsers.base import BaseManifestParser

FRAMEWORK_MAP = {
    "next": "Next.js",
    "react": "React",
    "vue": "Vue",
    "nuxt": "Nuxt",
    "@angular/core": "Angular",
    "express": "Express",
    "@nestjs/core": "NestJS",
    "fastify": "Fastify",
    "svelte": "Svelte",
    "@remix-run/react": "Remix",
    "astro": "Astro",
    "gatsby": "Gatsby",
}

TEST_MAP = {
    "jest": "Jest",
    "vitest": "Vitest",
    "mocha": "Mocha",
    "cypress": "Cypress",
    "@playwright/test": "Playwright",
    "playwright": "Playwright",
    "jasmine": "Jasmine",
    "@testing-library/react": "React Testing Library",
}

LINTER_MAP = {
    "eslint": "ESLint",
    "prettier": "Prettier",
    "@biomejs/biome": "Biome",
    "stylelint": "Stylelint",
    "tslint": "TSLint",
}

BUILD_MAP = {
    "vite": "Vite",
    "webpack": "Webpack",
    "rollup": "Rollup",
    "turbo": "Turborepo",
    "turborepo": "Turborepo",
    "esbuild": "esbuild",
    "tsup": "tsup",
    "parcel": "Parcel",
}


class NodeManifestParser(BaseManifestParser):
    """Parser for Node.js / TypeScript package.json files."""

    def can_parse(self, filename: str) -> bool:
        return Path(filename).name == "package.json"

    def parse(self, content: str, filename: str) -> ParsedManifest:
        data = json.loads(content)
        deps: dict[str, str] = {str(k): str(v) for k, v in data.get("dependencies", {}).items()}
        dev_deps: dict[str, str] = {str(k): str(v) for k, v in data.get("devDependencies", {}).items()}
        all_deps = {**deps, **dev_deps}

        is_ts = "typescript" in all_deps or any(k.startswith("@types/") for k in all_deps)
        language = "TypeScript" if is_ts else "JavaScript"

        frameworks = [v for k, v in FRAMEWORK_MAP.items() if k in all_deps]
        test_frameworks = [v for k, v in TEST_MAP.items() if k in all_deps]
        linters = [v for k, v in LINTER_MAP.items() if k in all_deps]
        build_tools = [v for k, v in BUILD_MAP.items() if k in all_deps]

        scripts = data.get("scripts", {})
        metadata = {
            "name": data.get("name", ""),
            "version": data.get("version", ""),
            "scripts": list(scripts.keys()),
        }

        return ParsedManifest(
            manifest_path=filename,
            language=language,
            ecosystem="node",
            dependencies=deps,
            dev_dependencies=dev_deps,
            frameworks=sorted(list(set(frameworks))),
            test_frameworks=sorted(list(set(test_frameworks))),
            linters_and_formatters=sorted(list(set(linters))),
            build_tools=sorted(list(set(build_tools))),
            metadata=metadata,
        )
