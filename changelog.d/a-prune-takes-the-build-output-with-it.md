PATCH

**`make verify` passes straight after a prune, with no `target/` to delete by hand.** Maven never removes an
output whose source has gone, so pruning Postgres from a Quarkus service left its `META-INF/services`
config-source registration in `target/classes`, and the next test run's ServiceLoader failed on a class nothing
compiled any more. Every feature's prune row now owns the service's `target/`, which the next build regenerates.
The postgres row also owns `META-INF/spring.factories`, where Spring Boot 4 registers the `DATABASE_URL`
post-processor.
