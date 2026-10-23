MINOR

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
