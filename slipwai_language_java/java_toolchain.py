"""Java's toolchain, which is Maven's: how a service of either framework installs, checks and caches itself.

These are the `java` family's answers to the toolchain members of the backend protocol
(`src/slipwai/registry.py`, whose shapes are fixed in
`specs/001-slipwai-2-language-addons/contracts/backend-protocol.md`). Every answer in `FAMILY` is the build
tool's rather than a framework's — the same wrapper resolves, the same goals run the gate, the same image
carries it — so it is written once here and both `java-quarkus` and `java-spring` inherit it. What the two
frameworks genuinely disagree about, how a service starts and what `make mutation` runs, each answers on its
own backend, built from `maven_dev_command` and `maven_native_commands` below. A sibling that built with
Gradle would answer `tooling`, `executables` and `compose_caches` on its own backend instead.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ... import registry as protocol
from ...backends import APP, Tooling
from ...tooling import for_app

# Every Maven invocation this factory writes, spelled once. `-B` because a recipe is never at a terminal
# and Maven's progress animation is noise in a CI log; `-q` because a passing gate should say nothing.
#
# `./mvnw`, not `mvn`. Maven was the one unpinned tool in a backend where Quarkus, Temurin, Checkstyle,
# PMD, SpotBugs, Error Prone and NullAway are all pinned exactly, and a wrapper is how this ecosystem
# spells that pin. The default wrapper genuinely cannot ship from here — it needs a `maven-wrapper.jar`
# beside the script and `assets/` is text or it is nothing — but `-Dtype=only-script` emits three text
# files and no jar, which is what `assets/languages/java/build/` carries — the language family's tree,
# shared by both Java backends, because a build wrapper belongs to Maven rather than to whatever owns
# startup above it.
#
# The download this adds is a distribution per `maven-wrapper.properties`, not per build:
# `actions/setup-java@v5` caches `~/.m2/wrapper/dists` under its own key derived from that file alone
# (`additionalCaches`, so `cache-dependency-path`'s pom does not rotate it), and `compose_caches` already
# holds the whole of `/root/.m2` for the containers. The fetch itself needs very little of an image: curl
# or wget, or failing both a `Downloader.java` the script compiles with the JDK, and it takes the `.tar.gz`
# where `unzip` is missing — which is what happens in `ci_image` below, and is proven by `make demo`.
MAVEN = f"cd {APP} && ./mvnw -B -q"

# Resolve and compile everything the gate will need, main and test alike. There is no `mvn install-deps`: in Maven,
# downloading dependencies is a side effect of needing them, so the honest spelling of "install" is the first build.
MAVEN_READY = f"{MAVEN} -DskipTests test-compile"

# What has to be installed inside `ci_image` before `make` can run there.
#
# Almost always nothing: `node:`, `python:` and `golang:` all ship GNU Make, so their containers run the
# same `make dev` a laptop does with no preamble. No official Maven or JDK image ships it — checked across
# `maven:*-eclipse-temurin-25`, its `-noble` and `-alpine` variants, and `eclipse-temurin:25-jdk` — so a
# Java container has to install it, and both places that run `make` inside a container need to know.
#
# A Dockerfile would be the other answer, and it is the wrong one here: `make demo` runs the checkout rather than a
# built image precisely so a demo can never be a stale copy of the code, and so there is no second definition of the
# app's layout to keep in step. One `apt-get` at container start is the cheaper side of that trade.
MAVEN_CONTAINER_SETUP = "apt-get update -qq && apt-get install -y -qq --no-install-recommends make"

# Where a containerised build writes, which for this backend has to be said in the environment rather than
# arranged with a volume.
#
# `MAVEN_ARGS` is applied to every `./mvnw` invocation in the container, and `service.build.dir` is the pom
# property the build directory is declared through — `project.build.directory` is read-only, so there is no
# way to move the output from the command line without that indirection. The path is outside `/workspace`,
# so nothing about the build touches the mounted checkout at all: no root-owned `target/`, and a host-side
# `make verify` still works immediately after `make demo`.
MAVEN_CONTAINER_ENVIRONMENT = {"MAVEN_ARGS": "-Dservice.build.dir=/tmp/service-build"}

# Where the two frameworks genuinely differ is `dev_command`, which each answers on its own backend.
# Writing these seven fields out twice would work on the day it was written and be two places to fix
# afterwards.
TOOLING: Tooling = {
    "install": MAVEN_READY,
    # Flyway's own Maven plugin is not what runs this, and the reason is the URL shape: every other
    # backend here reads the libpq-style `DATABASE_URL`, while JDBC needs `jdbc:postgresql://…` with the
    # credentials supplied apart from the host. Something has to translate, and doing it in a Make
    # recipe would put a second parser beside the one `config/DatabaseUrl.java` already has — two
    # parsers for one URL, drifting in a way no gate would catch. So the command runs a main that calls
    # Flyway through that single parser. Flyway still owns everything a migration runner is: the
    # ordering by `V<n>__`, the `flyway_schema_history` ledger, and applying each file in one
    # transaction. `<mainClass>` is configured in the pom rather than named here, because the package
    # carries this project's own name and the Makefile does not know it.
    "migrate": f"{MAVEN} -DskipTests compile exec:java",
    # Failsafe rather than Surefire, which is the whole `*Test` / `*IT` split: `make verify` runs
    # Surefire and never compiles a database into the gate. Invoked as goals rather than through
    # `verify`, so this target runs the integration suite and only that.
    "integration": f"{MAVEN} test-compile failsafe:integration-test failsafe:verify",
    "ci_image": "maven:3.9.16-eclipse-temurin-25-noble",
    "ci_install": MAVEN_READY,
    "container_setup": MAVEN_CONTAINER_SETUP,
    "container_environment": MAVEN_CONTAINER_ENVIRONMENT,
}

# Seven of the eight targets (`native_commands.TARGETS`), in that order, and word for word the same for both
# frameworks: everything a Maven build does is a goal, and the configuration those goals read is what
# differs, which lives in each pom. What is genuinely different is `mutation`, which each backend supplies.
MAVEN_GATE = {
    "install": MAVEN_READY,
    # javac *is* the type checker, so this target is "compile, with the checks that ride along":
    # Error Prone augments javac's own analysis and NullAway adds null-safety to it, both as
    # compiler plugins rather than a separate pass. `test-compile` so the test sources are held to
    # the same standard as the code they exercise.
    "typecheck": f"{MAVEN} -DskipTests test-compile",
    # Three analysers, and the compile they all need: SpotBugs reads bytecode, so `target/classes`
    # has to exist before it runs. Checkstyle is the standard, PMD the source-level rule set, and
    # each has its own committed configuration under the service's `config/` — tune the rules
    # there rather than dropping a gate here.
    "lint": f"{MAVEN} -DskipTests compile checkstyle:check pmd:check spotbugs:check",
    "test": f"{MAVEN} test",
    "integration": f"{MAVEN} test-compile failsafe:integration-test failsafe:verify",
    # A JUnit 5 tag rather than a name pattern, and `failIfNoTests=false` because a project that
    # has not written an adversarial test yet must still have a target that passes.
    "adversarial": f"{MAVEN} test -Dgroups=adversarial -DfailIfNoTests=false",
    "audit": (
        "@command -v osv-scanner >/dev/null 2>&1 || { echo 'install osv-scanner to run "
        f"dependency audit' >&2; exit 2; }}; osv-scanner scan source --recursive {APP}"
    ),
}


def maven_native_commands(mutation: str) -> Callable[[str, str], dict[str, str]]:
    """A framework's `native_commands`: Maven's seven shared targets, and its own `mutation`."""
    recipes = {**MAVEN_GATE, "mutation": mutation}

    def native_commands(path: str, verify: str) -> dict[str, str]:
        return {target: for_app(command, path, verify) for target, command in recipes.items()}

    return native_commands


def maven_dev_command(goal: str) -> Callable[[str, str, str], str]:
    """A framework's `dev_command`: the Maven goal that runs it in the foreground, in the service's directory."""

    def dev_command(qualifier: str, path: str, verify: str) -> str:
        return f"{MAVEN.replace(APP, path)} {goal}"

    return dev_command


# Where a Maven project's driven adapters live, for prose that has to point at them: `src/main/java` is the
# build tool's convention and neither framework moves it.
def event_store_directory(path: str) -> str:
    """Where one service's driven adapters live, for prose that has to point at them."""
    return f"{path}/src/main/java/com/example/<package>/adapters/driven/"


FAMILY: dict[protocol.Member[Any], object] = {
    protocol.TOOLING: TOOLING,
    protocol.FEATURE_TOOLING: {},
    # The wrapper belongs to Maven, not to whatever owns startup above it, so the two frameworks cannot
    # disagree about it while they share a build tool. `mvnw` and not `mvnw.cmd`: the wrapper plugin marks
    # only the shell script executable, and a `.cmd` has no use for the bit.
    protocol.EXECUTABLES: frozenset({f"{APP}/mvnw"}),
    # Only `~/.m2`, which sits outside the mounted checkout and so is exactly what an anonymous volume is
    # for. The build output is handled the other way — see MAVEN_CONTAINER_ENVIRONMENT. Masking
    # a service's `target/` with a volume keeps the class files out of the host tree but still
    # has Docker create the mount point on the host, owned by root, and the next host-side `./mvnw` then
    # fails with a permission error nowhere near its cause.
    protocol.COMPOSE_CACHES: ("/root/.m2",),
    protocol.EVENT_STORE_DIRECTORY: event_store_directory,
    # No formatter, and `None` is the answer: `make verify` checks the style through Checkstyle, and the
    # family contributes no `format` line.
    protocol.FORMATTER: None,
}
