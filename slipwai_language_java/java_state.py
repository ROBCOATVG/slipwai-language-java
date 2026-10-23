"""The state-stored rung's rows, which both Java frameworks share: the repository port, its three adapters, the
contract they all pass, and the versioned table Flyway creates.

A service answered `write-model: state` is given these instead of the event log (`rungs.rung_rows` reads the
`state` block of `write_side_files` for it, and nothing else). Everything below names no framework type — the
Postgres adapter takes a plain `DataSource`, which Hikari and Agroal both are — so it is written once here, the way
the event-store adapters are shared as `../java/` sources. What each framework adds is what touches it: how the
datasource learns `DATABASE_URL`, the integration test that needs an application context, and its transport and
identity rows, which a state service needs exactly as an event-sourced one does.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .java import JAVA_PORTS

MAIN = "src/main/java/com/example/deliverystarter"
TEST = "src/test/java/com/example/deliverystarter"

STATE_WRITE: dict[str, dict[str, str]] = {
    "memory": {
        f"{JAVA_PORTS}/state/Repository.java": "../java/repository.java",
        f"{JAVA_PORTS}/state/VersionedState.java": "../java/versioned_state.java",
        f"{JAVA_PORTS}/state/SaveResult.java": "../java/save_result.java",
        f"{JAVA_PORTS}/state/StateValues.java": "../java/state_values.java",
        f"{MAIN}/adapters/driven/repositorymemory/InMemoryRepository.java": "../java/repository_memory.java",
        f"{TEST}/repositorycontract/RepositoryContract.java": "../java/tests/repository_contract.java",
        f"{TEST}/adapters/driven/repositorymemory/InMemoryRepositoryTest.java": (
            "../java/tests/repository_memory_test.java"
        ),
    },
    "sqlite": {
        f"{MAIN}/adapters/driven/repositorysqlite/SqliteRepository.java": "../java/repository_sqlite.java",
        f"{TEST}/adapters/driven/repositorysqlite/SqliteRepositoryTest.java": (
            "../java/tests/repository_sqlite_test.java"
        ),
    },
    "postgres": {
        f"{MAIN}/adapters/driven/repositorypostgres/PostgresRepository.java": "../java/repository_postgres.java",
        # The rung's one table, under Flyway's convention from the shared `.sql` the way the event log's are.
        # A state service has no `events` table, so this is its V1.
        "src/main/resources/db/migration/V1__states.sql": "../sql/001_states.sql",
    },
}

# What a framework's event-rung `postgres` row carries that the state rung needs too: the URL parser and the
# framework's hook that feeds it to the datasource, the registration file that hook is found through, and the
# migration entry point. The adapters, the event schema and the event store's integration test stay behind.
SHARED_POSTGRES = ("/config/", "/META-INF/", "/migrations/")


def state_write_side(events: Mapping[str, Mapping[str, Any]], integration_test: str,
                     carried: tuple[str, ...]) -> dict[str, dict[str, str]]:
    """A framework's `state` block: the shared rows, its own datasource wiring taken from its event-rung
    `postgres` row, `integration_test` (its asset) as the Postgres repository's `*IT`, and the `carried`
    features — transport and identity — exactly as the event rung has them."""
    rows = {feature: dict(files) for feature, files in STATE_WRITE.items()}
    rows["postgres"].update({destination: source for destination, source in events["postgres"].items()
                             if any(part in destination for part in SHARED_POSTGRES)})
    rows["postgres"][f"{TEST}/adapters/driven/repositorypostgres/PostgresRepositoryIT.java"] = integration_test
    rows.update({feature: dict(events[feature]) for feature in carried})
    return rows
