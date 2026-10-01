"""The Java family's rows for the generated pruning script (`prune_rows`, S06), shared by both frameworks.

Written into a project's `scripts/backing-services.py` when it has a Java service, and read by the factory's own
pruner. The shape is fixed by the backend-protocol contract.

One family answer for Quarkus and Spring Boot, because they agree about all of it: the same marked files, the
same source layout, and nothing for a package manager to uninstall. They disagree in exactly one place, which
registration file the datasource configuration is found through, and both paths are named where they appear,
since a prune of a path this project does not have is a no-op. A framework that disagreed about something a
no-op could not cover would need rows of its own, and the pruner, which reads `project.json`'s `language`, would
need to read `backend` for it; nothing needs that yet.
"""
from __future__ import annotations

PRUNE_ROWS = {
    # Java's per-feature dependencies live in marked regions of the pom, and `application.properties` carries the
    # configuration that reads them. Both are comment-marked, so one mechanism removes a dependency and its
    # configuration together, which is why `package_edits` is empty and `manifest` is None: editing XML by
    # dropping lines is how a build file becomes unparseable.
    "marked_files": ("pom.xml", "src/main/resources/application.properties"),
    "owned_files": {
        "sqlite": (
            "src/main/java/com/example/*/adapters/driven/eventstoresqlite",
            "src/test/java/com/example/*/adapters/driven/eventstoresqlite",
            "src/main/java/com/example/*/adapters/driven/checkpointstoresqlite",
            "src/test/java/com/example/*/adapters/driven/checkpointstoresqlite",
        ),
        "postgres": (
            "src/main/java/com/example/*/adapters/driven/eventstorepostgres",
            "src/test/java/com/example/*/adapters/driven/eventstorepostgres",
            "src/main/java/com/example/*/adapters/driven/checkpointstorepostgres",
            "src/test/java/com/example/*/adapters/driven/checkpointstorepostgres",
            # The transaction seam and the framework bean behind it. Only the SQL store needs it: the in-memory
            # adapter is one lock and SQLite is one connection.
            "src/main/java/com/example/*/adapters/driven/sql",
            "src/main/java/com/example/*/config",
            "src/test/java/com/example/*/config",
            "src/main/java/com/example/*/migrations",
            "src/main/resources/db",
            # One of these per backend, never both: a MicroProfile `ConfigSource` under Quarkus and a Spring
            # `EnvironmentPostProcessor` under Spring Boot, each found through a registration file.
            "src/main/resources/META-INF/services",
            "src/main/resources/META-INF/spring",
        ),
        # Named file by file, because the auth adapter lives under `driving/http/` and dropping the transport
        # must not take it with it.
        "quarkus-rest": (
            "src/main/java/com/example/*/adapters/driving/http/SchemaFailure.java",
            "src/main/java/com/example/*/adapters/driving/http/NotFoundMapper.java",
            "src/main/java/com/example/*/adapters/driving/http/ServiceHealthCheck.java",
            "src/test/java/com/example/*/adapters/driving/http/HttpAppTest.java",
        ),
        "spring-web": (
            "src/main/java/com/example/*/adapters/driving/http/SchemaFailure.java",
            "src/main/java/com/example/*/adapters/driving/http/NotFoundAdvice.java",
            "src/main/java/com/example/*/adapters/driving/http/ServiceHealthIndicator.java",
            "src/test/java/com/example/*/adapters/driving/http/HttpAppTest.java",
        ),
        "keycloak": (
            "src/main/java/com/example/*/adapters/driving/http/auth",
            "src/test/java/com/example/*/adapters/driving/http/auth",
        ),
        "users-keycloak": (
            "src/main/java/com/example/*/adapters/driving/http/users",
            "src/test/java/com/example/*/adapters/driving/http/users",
        ),
    },
    "package_edits": {},
    "manifest": None,
}
