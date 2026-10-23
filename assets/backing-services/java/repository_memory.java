package com.example.deliverystarter.adapters.driven.repositorymemory;

import com.example.deliverystarter.application.ports.state.Repository;
import com.example.deliverystarter.application.ports.state.SaveResult;
import com.example.deliverystarter.application.ports.state.VersionedState;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

/**
 * The in-memory state repository: for a quickstart with no infrastructure, and for the tests that need a
 * repository rather than proof of concurrency.
 *
 * <p>{@code make verify} runs the shared contract against this one, which is why the gate needs no Docker. Every
 * call is serialised behind one lock, so it <strong>cannot</strong> prove that two independent writers at one
 * version produce exactly one winner — that guarantee is the real store's compare-and-swap, proved by
 * {@code make test-integration} on Postgres. Rows are lost when the process ends. Never production.
 */
public final class InMemoryRepository implements Repository {

    private final Map<String, VersionedState> rows = new HashMap<>();

    @Override
    public synchronized Optional<VersionedState> load(String id) {
        // VersionedState copies on construction and holds an unmodifiable copy, so handing out the stored row
        // shares nothing a caller could change.
        return Optional.ofNullable(rows.get(id));
    }

    @Override
    public synchronized SaveResult save(String id, int expectedVersion, Map<String, Object> state) {
        Repository.requireWritable(id, expectedVersion, state);
        VersionedState current = rows.get(id);
        int actualVersion = current == null ? NO_STATE : current.version();
        if (actualVersion != expectedVersion) {
            return SaveResult.versionConflict(actualVersion);
        }
        int version = actualVersion + 1;
        rows.put(id, new VersionedState(id, version, state));
        return SaveResult.saved(version);
    }

    @Override
    public synchronized long head() {
        return rows.size();
    }
}
