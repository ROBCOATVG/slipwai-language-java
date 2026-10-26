PATCH

**A Java service with a long name passes its own Checkstyle.** The doc comments on `MigrateMain` and `SeedMain` showed the command as one line beginning `cd apps/<service> &&`, which was already 115 characters for `apps/service`; a service added under a longer name, as `add-service` names a new home, went over the 120-character limit and `verify` failed on a file nobody wrote. The `cd` is now a line of its own.

**Catch-up.** A service already generated keeps the long line until it is regenerated; splitting the comment by hand is the whole fix.
