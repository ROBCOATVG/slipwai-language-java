"""The Java family's and its two frameworks' answers about the project around their services: what git ignores,
what an agent may run, what the gate is called, where the event model's code lives, and what `make mutation` is.

Moved here from core's per-backend tables (S05). What Maven decides is the family's (`FAMILY`), and both frameworks
inherit it; what the framework decides is each backend's (`QUARKUS`, `SPRING`): the build output left beside the pom,
the test harness the gate runs, and — the one place in the family where that is load-bearing — the mutation note.
PIT works under Spring Boot's test harness and times out under Quarkus's, so one backend's note explains a working
target and the other's explains why there is none; a family note would print the wrong one for one of them."""
from __future__ import annotations

from typing import Any

from ... import registry as protocol
from ...naming import java_package_segment
from ..renovate import RenovateRules

# What `make mutation` does on the Quarkus backend, and why it is not PIT already wired up.
#
# Per backend rather than per family, and the Spring sibling is the reason: PIT *is* wired up there, so a
# note shared across the family would tell one of the two something flatly untrue about its own build.
#
# PIT is the ecosystem's mutation tester and pitest-junit5-plugin 1.2.3 is the first version claiming
# Quarkus support — so the tool is not in doubt. What is in doubt is running it over a `@QuarkusTest`:
# pitest issue #1287 reports tests that pass standalone timing out on every mutation under PIT, on the
# configuration that behaves fine for Spring Boot — which is the one `java-spring` in this same factory
# ships wired up. That is exactly the failure this factory could not
# catch, because `make mutation` is run by no gate at either level (docs/backend-obligations.md section 2),
# so a wired-up PIT would have been committed green and stayed green.
#
# The mitigation is real and is written down below rather than guessed at later: mutate the domain, which
# is framework-free by construction here, with its plain JUnit tests — and keep `@QuarkusTest` and `*IT`
# out of PIT's reach. That is a decision about which classes this product considers worth mutating, which
# is why it is a decision the project makes rather than one the factory pins.
JAVA_QUARKUS_MUTATION_NOTE = """\
# Not wired up, on purpose, and the reason is a support constraint rather than a missing dependency.
#
# PIT is the JVM's mutation tester, and pitest-junit5-plugin 1.2.3 is the first version that claims
# Quarkus support. But pitest issue #1287 reports `@QuarkusTest` classes that pass standalone timing out
# on every mutation once PIT runs them — the same configuration works for Spring Boot, which is why the
# `java-spring` backend here ships `make mutation` wired up and this one does not. Nothing in this
# repository's gates runs this target, so a broken configuration here would never fail a build; it would
# just quietly never have worked.
#
# So configure it deliberately, and narrowly:
#
#   1. targetClasses — the domain packages only. They are framework-free by construction, which is the
#      whole reason the hexagon puts them there, and they are where a surviving mutant means something.
#   2. targetTests — the plain JUnit tests over those packages. Exclude `@QuarkusTest` and every `*IT`.
#   3. pitest-junit5-plugin as a dependency of the pitest-maven *plugin*, not of the project. Declared as
#      a project dependency, PIT reports "0 tests found" and does nothing, which is the most common way a
#      first PIT setup silently passes.
#
# Then run it, look at the survivors, and only afterwards let anything depend on the score.
"""

# What `make mutation` does on the Spring backend, where it is a working target rather than a placeholder.
#
# Emitted above the target for the same reason its sibling's note is: the next person to read a mutation
# score needs to know what was mutated before they trust it. Make comments do not match the `help` grep, so
# this stays out of `make help`.
JAVA_SPRING_MUTATION_NOTE = """\
# Wired up and scoped, and the scope is the part to read before trusting a score.
#
# PIT mutates the packages named in `pitest-maven`'s `targetClasses` in `__APP__/pom.xml` — the
# domain, the ports, the URL parser and the group mapping — and runs the plain `*Test` classes over them.
# That is deliberate on both sides:
#
#   1. Those packages are framework-free by construction, which is the whole reason the hexagon puts them
#      there, and they are where a surviving mutant means a rule nothing checks.
#   2. `*IT` is excluded. PIT runs the tests once per mutant, so a database suite in scope would turn a
#      minutes-long run into an hours-long one, for coverage of wiring rather than of rules.
#   3. Two classes inside those packages are excluded by name — `SecurityConfig` and the
#      `EnvironmentPostProcessor`. They are how a decision gets plugged into Spring rather than the
#      decision, so their mutants survive by nature: killing one would mean asserting Spring's own wiring.
#
# The report lands in `target/pit-reports/`. It fails rather than passes when it finds nothing to mutate,
# which is deliberate: `failWhenNoMutations` is `true` in the pom because "0 mutations" here can only mean
# a misconfigured run, and a silent pass on a target no gate runs is worse than a red one.
#
# So a clean run here does NOT mean the adapters are well tested; it means the rules are. Widen
# `targetClasses` as use cases arrive, and leave the adapters out — their tests are about wiring, and
# mutating wiring mostly produces survivors nobody should act on.
#
# No threshold is set. A score nobody has looked at yet is not a gate, and this target is run by no gate at
# either level (docs/backend-obligations.md section 2) — so read the survivors, then decide.
"""

JAVA_QUARKUS_MUTATION_PLACEHOLDER = (
    "@echo 'Configure PIT for the domain packages only — see the note above this target — then run it.'; "
    "exit 2"
)


# What a Java project still owes for each identity provider, per feature. The family's, so both frameworks say it
# (D34: the paragraph names `quarkus-oidc` to a Spring project too, and is carried here byte for byte until a
# slice of its own gives `java-spring` its own answer).
IDENTITY_OUTSTANDING = {
    "keycloak": """**The protocol flow is `quarkus-oidc`'s**, not this project's: the Authorization Code flow with
PKCE, the JWKS retrieval and the full token validation all come from the extension, and none of it should
ever be written here. It is configured in `apps/service/src/main/resources/application.properties` and
deliberately left disabled — enabled, the service refuses to boot whenever Keycloak is not up, which is a
hard dependency bought for nothing until a route needs a principal. What this project still owns is the
group-to-role mapping in `KeycloakRoles`, and naming the roles it maps.""",
    "users-keycloak": """**Token validation is the framework's**, configured for the `customers` realm in
`apps/service/src/main/resources/application.properties` and deliberately left disabled until a route needs a
customer. What this project owns is `CustomerIdentity`: a validated token becomes a customer only if its issuer
is exactly this realm's — a staff token is a valid JWT too — and its email is verified.""",
}


def maven_paths(project_name: str, service: str) -> dict[str, str]:
    """Maven's source roots rather than a framework's, which is why both Java backends share them. Java drops the
    separators rather than replacing them, the way the ecosystem does with a hyphenated artifact name, and a segment
    that would start with a digit gets the same prefix treatment."""
    documented_java_segment = java_package_segment(project_name)
    documented_java_path = f"{service}/src/main/java/com/example/{documented_java_segment}"
    return {
        "events": f"{documented_java_path}/domain/<context>/Events.java",
        "domain": f"{documented_java_path}/domain/<context>/Decider.java",
        "usecase": f"{documented_java_path}/application/<context>/<UseCase>.java",
        "test": (
            f"{service}/src/test/java/com/example/{documented_java_segment}"
            "/domain/<context>/<Slice>Test.java (JUnit 5)"
        ),
    }


FAMILY: dict[protocol.Member[Any], object] = {
    protocol.PROCFILE: None,
    protocol.PIN_FILES: {},
    protocol.MAKEFILE_VARIABLES: None,
    protocol.RENOVATE_RULES: RenovateRules(
        ("maven",), ("maven", ("maven",), "the Maven builds, including the plugins the gate's analysers are"), None
    ),
    protocol.OPT_IN_FLAG_TRANSPORTS: frozenset(),
    protocol.IDENTITY_OUTSTANDING: IDENTITY_OUTSTANDING,
    # One entry point rather than several binaries: everything a Maven toolchain does — compile, test, the three
    # analysers, dev mode — is a goal, so approving `./mvnw` is approving the toolchain. The wrapper and not
    # `mvn`: that is the only spelling either Java backend's gates use, which is also why both share this.
    protocol.AGENT_PERMISSIONS: ["./mvnw *"],
    protocol.EVENT_MODEL_PATHS: maven_paths,
    protocol.MUTATION_TOOL: "PIT (pitest)",
}
QUARKUS: dict[protocol.Member[Any], object] = {
    # `target/` is every artifact Maven writes — classes, the Quarkus build output, the analysers'
    # reports. `.flattened-pom.xml` is what the Quarkus build leaves behind when it resolves the
    # platform BOM, and it is derived from the pom rather than edited beside it.
    protocol.GITIGNORE: "target/\n.flattened-pom.xml\n",
    protocol.GATE_DESCRIPTION: (
        "Checkstyle, PMD and SpotBugs for lint; `javac` with Error Prone and NullAway for the type check; "
        "JUnit 5 with Quarkus's own test harness, coverage through the `quarkus-jacoco` extension"
    ),
    protocol.MUTATION_NOTE: JAVA_QUARKUS_MUTATION_NOTE,
}
SPRING: dict[protocol.Member[Any], object] = {
    # `target/` for the same reason, and nothing else: Spring Boot's plugin writes the repackaged jar
    # and the `build-info` inside it rather than beside the pom, so there is no second file to ignore.
    protocol.GITIGNORE: "target/\n",
    protocol.GATE_DESCRIPTION: (
        "Checkstyle, PMD and SpotBugs for lint; `javac` with Error Prone and NullAway for the type check; "
        "JUnit 5 with Spring Boot's test harness and MockMvc, coverage through JaCoCo"
    ),
    protocol.MUTATION_NOTE: JAVA_SPRING_MUTATION_NOTE,
}
