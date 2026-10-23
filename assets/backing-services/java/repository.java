package com.example.deliverystarter.application.ports.state;

import java.util.Map;
import java.util.Optional;

/**
 * The state-stored write model's port: one current row per id, and the version that guards it.
 *
 * <p>A service answered {@code write-model: state} keeps what a decision produced rather than the facts that led
 * to it. There is no log to replay, so the version is the whole of the concurrency story: a use case loads a row,
 * decides against the version it read, and saves at that version. A save at any other version is refused as a
 * value, {@link SaveResult.VersionConflict}, never an exception — a lost race is an outcome the caller decides
 * what to do with, usually by loading again.
 *
 * <p>The in-memory adapter, SQLite and Postgres all satisfy one contract ({@code RepositoryContract}); the
 * in-memory one serialises every call behind a lock, so only Postgres proves that two independent writers at
 * one version produce exactly one winner. That is {@code make test-integration}'s job.
 *
 * <p>State is a JSON object — the shape every adapter can store without changing it. {@link StateValues}
 * refuses anything else before a row is touched, so a value the memory fake would keep and SQL would mangle
 * fails in {@code make verify} rather than in production.
 *
 * <p>Not a bean, and neither is any adapter behind it: which store a service uses is a composition decision,
 * and the first slice that needs one writes the producer (a {@code @Bean} method under Spring Boot, a
 * {@code @Produces} method under Quarkus) the way the event-sourced rung does.
 */
public interface Repository {

    /** The version a caller expects when the row does not exist yet. A first save lands at version 0. */
    int NO_STATE = -1;

    /** The row for {@code id}, or empty when nothing has been saved under it. */
    Optional<VersionedState> load(String id);

    /**
     * Save {@code state} under {@code id} if the stored version is still {@code expectedVersion}.
     *
     * <p>{@link #NO_STATE} creates the row; any other value updates it. Neither can manufacture a row the
     * other should have: an update of a missing row is a conflict at {@link #NO_STATE}, and a create over an
     * existing one is a conflict at its version.
     *
     * @throws IllegalArgumentException when {@code id} is blank, {@code expectedVersion} is below
     *     {@link #NO_STATE}, or {@code state} is not a JSON object — before anything is written
     */
    SaveResult save(String id, int expectedVersion, Map<String, Object> state);

    /**
     * How many rows the store holds, for a readiness check that wants proof the store answers. The
     * state-stored rung's equivalent of the event store's head, and deliberately nothing more.
     */
    long head();

    /** The checks every adapter makes before it writes, in one place so no adapter forgets one. */
    static void requireWritable(String id, int expectedVersion, Map<String, Object> state) {
        if (id.isBlank()) {
            throw new IllegalArgumentException("state repository requires an id");
        }
        if (expectedVersion < NO_STATE) {
            throw new IllegalArgumentException("expectedVersion must be NO_STATE or a non-negative version");
        }
        StateValues.requireJson(state);
    }
}
