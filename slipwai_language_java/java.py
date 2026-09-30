"""What both Java backends do the same way, whichever framework owns their startup.

A third module rather than a helper inside one of the siblings, and the reason is the import direction
`scripts/check-structure.py` enforces: a function `java_spring` reached for by importing `java_quarkus`
would make the two backends depend on each other, and the next thing either of them needed from the other
would close the loop. Both import this; neither imports the other.

What belongs here is what the *language* decides rather than the framework: Maven's source layout, how a
project name becomes a package segment, and the fact that every Java file names its own package. What does
not is anything a framework has an opinion about — the pom, the properties, the adapters. Those are the
siblings' own, and `assets/languages/java/build/` is where their shared *content* lives.
"""
from __future__ import annotations

from ... import registry as protocol
from ...naming import java_package_segment
from ...services import App
from ...tooling import service_qualifier
from ..ci_workflows import dependency_paths
from . import java_toolchain as toolchain

# The package every committed asset is written under, and the artifact id in the committed pom. Both are
# rewritten to this project's own names below — every Java file names its package and imports its siblings
# by it, so rewriting only the pom would produce a project that does not compile.
TEMPLATE_SEGMENT = "deliverystarter"
TEMPLATE_ARTIFACT = "delivery-starter-service"


def rename_java_sources(project_name: str, service: App, files: dict[str, str]) -> dict[str, str]:
    """Move one service's files under this project's own package, contents and path alike.

    Both the directory and the `package`/`import` lines inside it, because in Java those are one fact
    stated twice: a file at `com/example/acme/events/` that declares `package com.example.deliverystarter`
    does not compile, and neither does its sibling that imports the old name. The first service's package is
    named after the project alone, as it always was; a later one is `com.example.<project><service>`, one
    flattened segment, the way this ecosystem flattens a hyphenated artifact name.
    """
    segment = java_package_segment(service_qualifier(project_name, service))
    for path in list(files):
        if not path.startswith(f"{service.path}/"):
            continue
        content = files.pop(path)
        # The artifact id first: it contains a hyphen, so it can never be confused with the package
        # segment, and replacing the segment first would leave `delivery-starter-service` half-rewritten.
        content = content.replace(TEMPLATE_ARTIFACT, f"{project_name}-{service.name}")
        content = content.replace(TEMPLATE_SEGMENT, segment)
        files[path.replace(TEMPLATE_SEGMENT, segment)] = content
    return files


def verify_script(services: list[App]) -> str:
    """Everything `make verify` runs natively, in one script, for whoever has not read the Makefile yet.

    Deliberately not the whole gate — the repository-level checks are Python and belong to `make`. The same
    for both frameworks because every command in it is Maven's or a plugin's rather than the framework's:
    what changes between the siblings is what those plugins are configured with in each pom.

    One Maven project per service, and this loop is the aggregator: each service keeps its own pom with its
    own framework parent, `add-service` copies a skeleton rather than editing a module list, and nothing at
    the root has to be kept in step. A shared Maven module under `packages/` is what would change that — a
    reactor is how one build orders a library before the services that depend on it.
    """
    apps = " ".join(service.path for service in services)
    return f"""#!/bin/sh
set -eu
for app in {apps}; do
  (
    cd "$app"
    ./mvnw -B -q -DskipTests compile checkstyle:check pmd:check spotbugs:check
    ./mvnw -B -q -DskipTests test-compile
    ./mvnw -B -q test
  )
done
"""


def ci_toolchain_setup(services: list[App]) -> str:
    """One `actions/setup-java` for every Java service, whichever framework owns its startup.

    Which JDK to install and where the dependency cache lives are the toolchain's answers rather than a
    framework's, so both Java backends inherit this one. Temurin 25 is the current LTS, the floor Quarkus
    3.33's AOT cache generation needs and well inside Spring Boot 4.1's 17-to-26 range. `cache: maven` keys
    on the poms, so a run that changes no dependency downloads nothing; it also covers the Maven the wrapper
    fetches, which `setup-java@v5` caches under a second key derived from `maven-wrapper.properties` alone.
    """
    return (
        "      - uses: actions/setup-java@v5\n        with:\n          distribution: temurin\n"
        "          java-version: '25'\n          cache: maven\n"
        f"          cache-dependency-path: {dependency_paths([f'{s.path}/pom.xml' for s in services])}\n"
    )


# The family only: Maven, the source layout and the package rule are shared, and each framework declares its own
# backend beside this in `java_quarkus.py` and `java_spring.py`. Maven's toolchain answers and the CI toolchain
# step are the family's, and both frameworks inherit them (`java_toolchain.py`).
LANGUAGE = protocol.Language(families=(protocol.Family("java", toolchain.FAMILY | {
    protocol.CI_TOOLCHAIN_SETUP: ci_toolchain_setup,
}),))
