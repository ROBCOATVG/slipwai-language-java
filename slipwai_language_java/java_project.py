"""The Java family's answers about the project around its services: what an agent may run, where the event model's
code lives, what an identity provider still owes, and which mutation tool the family uses.

Moved here from core's per-backend tables (S05). What Maven decides is the family's (`FAMILY`), and both frameworks
inherit it; what the framework decides — the build output left beside the pom, the test harness the gate runs, and
the mutation note, which differs because PIT works under Spring Boot's test harness and times out under Quarkus's —
is each framework package's own (`quarkus_project.py` in `java-quarkus`, `spring_project.py` in `java-spring`)."""
from __future__ import annotations

from typing import Any

from slipwai import registry as protocol
from slipwai.naming import java_package_segment
from slipwai.project.renovate import RenovateRules

# What a Java project still owes for each identity provider, per feature. The family's, so both frameworks say it
# (D34: the `keycloak` paragraph names `quarkus-oidc`, so `java-spring` answers its own, in its own package,
# and takes this `users-keycloak` one from here).
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
