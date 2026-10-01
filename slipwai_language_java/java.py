"""What both Java backends do the same way, whichever framework owns their startup.

A third module rather than a helper inside one of the siblings, and the reason is the import direction
`scripts/check-structure.py` enforces: a function `java_spring` reached for by importing `java_quarkus`
would make the two backends depend on each other, and the next thing either of them needed from the other
would close the loop. Both import this; neither imports the other.

What belongs here is what the *language* decides rather than the framework: Maven's source layout, how a
project name becomes a package segment, and the fact that every Java file names its own package. What does
not is anything a framework has an opinion about — the pom, the properties, the adapters. Those are the
siblings' own, and `assets/languages/java/build/` is where their shared *content* lives.

This is the `java` language package: a family with no backend of its own. Core loads it from the language
directory; the frameworks (`java-quarkus`, `java-spring`) are packages of their own that require it, import what they
share from it, and read its files after their own. Its assets are the `assets/` beside this package.
"""
from __future__ import annotations

from pathlib import Path

from slipwai import registry as protocol
from slipwai.naming import java_package_segment
from slipwai.project.ci_workflows import dependency_paths
from slipwai.project.flags import FlagReader
from slipwai.services import App
from slipwai.tooling import service_qualifier

from . import java_toolchain as toolchain
from .java_project import FAMILY as PROJECT
from .java_prune_rows import PRUNE_ROWS

# This package's own assets, the layout core's readers use for every language: `languages/java/…` and
# `backing-services/{java,sql}/`. The frameworks read `languages/java/build/` through this name.
ASSETS = Path(__file__).resolve().parents[1] / "assets"

# The package every committed asset is written under, and the artifact id in the committed pom. Both are
# rewritten to this project's own names below — every Java file names its package and imports its siblings
# by it, so rewriting only the pom would produce a project that does not compile.
TEMPLATE_SEGMENT = "deliverystarter"
TEMPLATE_ARTIFACT = "delivery-starter-service"
#: Where the two ports sit in Maven's layout: under the application layer, which owns them.
JAVA_PORTS = "src/main/java/com/example/deliverystarter/application/ports"


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


def repository_files(
    project_name: str, files: dict[str, str], services: list[App], verify: str
) -> dict[str, str]:
    """`scripts/verify` above the services, and nothing else.

    There is no aggregator pom above them: each service is a Maven project of its own, and one pom that
    exists only to list them is a file to keep in step for nothing — `scripts/verify` and the Makefile are
    the loop. Compare `go.work`, which Go genuinely requires. The family's, because both frameworks wrote it the
    same way: a framework that wanted an aggregator would answer its own.
    """
    files[verify] = verify_script(services)
    return files


# The flag reader, once for both backends: it reads one committed tree, `java/flags`, for the reason they share
# `java/build/` and every `../java/` source in their layouts. The class names no framework type — no
# `@ConfigProperty`, no `@Value` — so a second copy would have nothing to say differently and could only drift.
READER = FlagReader(
    tree="java/flags",
    source="src/main/java/com/example/deliverystarter/flags/Flags.java",
    tests="src/test/java/com/example/deliverystarter/flags/FlagsTest.java",
    call='Flags.enabled("checkout-v2")',
)


# What "code shared between services" is in this family, and what sharing it would ask of the build: the
# architecture page's paragraph. The family's answer rather than a backend's, because the unit of sharing is
# the build tool's rather than the framework's — and this is where the question of an aggregator
# pom is answered, so it is answered where a reader of the generated project will look for it.
SHARED = (
    "a Maven module under `packages/<name>` that each service's pom depends on. Every service is a Maven "
    "project of its own today, with `scripts/verify` and the Makefile as the loop that builds them; a "
    "shared module the services have to build first is what would make an aggregator pom worth having, "
    "and that is the day to add one"
)


# The family only: Maven, the source layout and the package rule are shared, and each framework declares its own
# backend beside this in its own package (`java-quarkus`, `java-spring`). Maven's toolchain answers, the CI toolchain
# step, the flag reader, the shared-code paragraph, the pruner's rows, the rename and the root `scripts/verify`
# are the family's, and both frameworks inherit them (Story 1 scenario 4).
LANGUAGE = protocol.Language(families=(protocol.Family("java", toolchain.FAMILY | PROJECT | {
    protocol.NAME_SERVICE: rename_java_sources,
    protocol.REPOSITORY_FILES: repository_files,
    protocol.CI_TOOLCHAIN_SETUP: ci_toolchain_setup,
    protocol.FLAG_READER: READER,
    protocol.SHARED_CODE: SHARED,
    protocol.PRUNE_ROWS: PRUNE_ROWS,
}),))
