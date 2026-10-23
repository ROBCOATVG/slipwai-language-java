# Changelog

No releases yet. Release notes are recorded here newest first, one entry per released version; the entry being
written is `changelog.d/`.

## 1.2.0 — MINOR

**`make verify` passes straight after a prune, with no `target/` to delete by hand.** Maven never removes an
output whose source has gone, so pruning Postgres from a Quarkus service left its `META-INF/services`
config-source registration in `target/classes`, and the next test run's ServiceLoader failed on a class nothing
compiled any more. Every feature's prune row now owns the service's `target/`, which the next build regenerates.
The postgres row also owns `META-INF/spring.factories`, where Spring Boot 4 registers the `DATABASE_URL`
post-processor.

**A Java service on the durable event store may be given a story's inputs, through its own seed door.** The
family's `SEED_DOOR` rows bring `seed/SeedMain.java` and its `SeedTest`, and the toolchain answers the `seed`
line, so `make seed-<service> FILE=<json>` runs `exec:java@seed`: it appends the events a slice's `try-it.json`
gives through the event-store port, at the stream's current version, as the system actor `systems/seed-door` under
one correlation id per run, with an identity hashed from stream, type and canonical data so a re-run appends
nothing. With no `DATABASE_URL` it says so and exits 2. Never an HTTP route: the door is a process with the
store's credentials. A command that exits has no framework transaction manager to borrow, so it brings
`SeedTransactions`, the event store's `Transactions` port kept by the one connection the process opened (no thread
binding, savepoints for nested work). The prune rows own `seed/` with postgres. Event rung only: the keel writes a
state-stored service no seed target.

**Catch-up:** `slipwai language upgrade java` with the framework package, then `slipwai migrate`; the service
gains the seed package and the pom's `seed` execution, and the Makefile its target. Until then a story's `given`
is validated by `check-try` and not applied.

## 1.1.0 — MINOR

**A Java service answered `write-model: state` is given a versioned repository instead of the event log.** The
family now carries the state-stored rung's shared rows (`java_state.py`): the `Repository` port under
`application/ports/state/` with `NO_STATE`, `VersionedState` and a `SaveResult` that returns a lost race as a
value; in-memory, SQLite and Postgres adapters behind it, the Postgres one comparing and incrementing the version
in one statement over the application's own `DataSource`; one `RepositoryContract` all three pass; and
`V1__states.sql`, a `states` table whose state is a checked JSON object. `event_model_paths` answers `repository`,
the toolchain answers `persistence_directory` (the member `event_store_directory` was renamed to), and the prune
rows own the two new adapter directories with their stores. The event-sourced rung is unchanged.

**Catch-up:** `slipwai language upgrade java` together with the framework package; an existing event-sourced
service changes nothing, and a new state-stored one is generated with `--write-model state`.

## 1.0.0

**Java is now a language family package of its own.** What both Java backends that were built into slipwai
share — Maven's toolchain and wrapper, the analyser configuration, the source layout and package rename, the
event-store and read-model adapters, the flag reader, the pruner's rows and the example snippets — lives here,
with the history it had there. It owns no backend: `java-quarkus` and `java-spring` are framework packages that
require it (`requires: {"java": ">=1.0,<2"}`), and `language.json` names `quarkus` as the framework `--language java`
defaults to. slipwai loads it from its language directory (`$SLIPWAI_LANGUAGES`, or `~/.slipwai/languages`), and the
projects it generates are byte for byte those slipwai generated with Java built in. It declares the catalog schema
it loads on, `core >=9.0,<10`.

