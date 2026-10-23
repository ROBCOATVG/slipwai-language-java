# slipwai-language-java
slipwai 2.0 language addon: slipwai-language-java

## Write models

Both rungs of `write-model` are answered for every Java framework. `events` keeps the event-store port, its
memory, SQLite and Postgres adapters, the projection runner and Flyway's `V1`–`V4` event schema. `state` gives a
service the `Repository` port under `application/ports/state/` instead: one current row per id, saved at the
version it was loaded at, with a lost race returned as `SaveResult.VersionConflict` rather than thrown. Its memory,
SQLite and Postgres adapters pass one `RepositoryContract`; the Postgres one compares and increments the version in
a single statement over the application's `DataSource`, and `V1__states.sql` is its schema. The shared rows are
`slipwai_language_java/java_state.py`; each framework adds its own datasource wiring and the integration test that
needs its application context.
