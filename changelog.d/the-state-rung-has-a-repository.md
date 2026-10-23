MINOR

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
