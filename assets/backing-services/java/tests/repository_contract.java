package com.example.deliverystarter.repositorycontract;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.example.deliverystarter.application.ports.state.Repository;
import com.example.deliverystarter.application.ports.state.SaveResult;
import com.example.deliverystarter.application.ports.state.VersionedState;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;

/**
 * One contract, run against every state-repository adapter: memory and SQLite in {@code make test}, Postgres in
 * {@code make test-integration}. No adapter gets its own version of the rule.
 *
 * <p>Every case works under a freshly generated id, so a shared Postgres table needs no cleaning between them.
 */
public abstract class RepositoryContract {

    private final String rowId = UUID.randomUUID().toString();

    /** Build the adapter under test. Called once per case. */
    protected abstract Repository newRepository();

    @Test
    void readsAnUnknownRowAsAbsent() {
        assertThat(newRepository().load(rowId)).isEmpty();
    }

    @Test
    void createsAtNoStateAndUpdatesOnlyAtTheVersionItRead() {
        Repository repository = newRepository();

        assertThat(repository.save(rowId, Repository.NO_STATE, Map.of("status", "draft")))
                .isEqualTo(SaveResult.saved(0));
        assertThat(repository.save(rowId, 0, Map.of("status", "confirmed"))).isEqualTo(SaveResult.saved(1));
        assertThat(repository.load(rowId)).contains(new VersionedState(rowId, 1, Map.of("status", "confirmed")));
    }

    @Test
    void refusesAStaleDecisionAndLeavesTheWinningStateAlone() {
        Repository repository = newRepository();
        repository.save(rowId, Repository.NO_STATE, Map.of("status", "draft"));
        repository.save(rowId, 0, Map.of("status", "confirmed"));

        assertThat(repository.save(rowId, 0, Map.of("status", "cancelled")))
                .isEqualTo(SaveResult.versionConflict(1));
        assertThat(repository.load(rowId).orElseThrow().state()).isEqualTo(Map.of("status", "confirmed"));
    }

    @Test
    void refusesToCreateOverAnExistingRow() {
        Repository repository = newRepository();
        repository.save(rowId, Repository.NO_STATE, Map.of("status", "draft"));

        assertThat(repository.save(rowId, Repository.NO_STATE, Map.of("status", "again")))
                .isEqualTo(SaveResult.versionConflict(0));
    }

    @Test
    void cannotManufactureAMissingRowFromANoninitialVersion() {
        Repository repository = newRepository();

        assertThat(repository.save(rowId, 0, Map.of("status", "confirmed")))
                .isEqualTo(SaveResult.versionConflict(Repository.NO_STATE));
        assertThat(repository.load(rowId)).isEmpty();
    }

    /**
     * Two decisions at one version, racing: exactly one wins. Against a store that serialises every call this
     * is a statement of the rule; against Postgres it is the proof.
     */
    @Test
    void givesExactlyOneOfTwoSameVersionDecisionsTheWin() throws Exception {
        Repository repository = newRepository();
        repository.save(rowId, Repository.NO_STATE, Map.of("writer", "original"));

        List<SaveResult> results = race(repository, repository, 0);

        assertThat(results).filteredOn(SaveResult.Saved.class::isInstance).hasSize(1);
        assertThat(results).filteredOn(SaveResult.VersionConflict.class::isInstance)
                .containsExactly(SaveResult.versionConflict(1));
        assertThat(repository.load(rowId).orElseThrow().version()).isEqualTo(1);
    }

    @Test
    void rejectsValuesThatWouldChangeWhenStoredAsJson() {
        Repository repository = newRepository();
        Map<String, Object> cyclic = new HashMap<>();
        cyclic.put("self", cyclic);
        for (Map<String, Object> state : List.of(
                Map.<String, Object>of("bad", Double.NaN),
                Map.<String, Object>of("bad", Instant.EPOCH),
                cyclic)) {
            assertThatThrownBy(() -> repository.save(rowId, Repository.NO_STATE, state))
                    .isInstanceOf(IllegalArgumentException.class)
                    .hasMessageContaining("JSON");
            assertThat(repository.load(rowId)).isEmpty();
        }
    }

    @Test
    void rejectsABlankIdAndAVersionBelowNoState() {
        Repository repository = newRepository();

        assertThatThrownBy(() -> repository.save(" ", Repository.NO_STATE, Map.of()))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> repository.save(rowId, -2, Map.of()))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void doesNotShareMutableObjectsWithTheCaller() {
        Repository repository = newRepository();
        Map<String, Object> nested = new HashMap<>(Map.of("count", 1));
        Map<String, Object> state = new HashMap<>(Map.of("nested", nested));

        repository.save(rowId, Repository.NO_STATE, state);
        nested.put("count", 10);

        assertThat(repository.load(rowId).orElseThrow().state()).isEqualTo(Map.of("nested", Map.of("count", 1)));
    }

    @Test
    void countsItsRowsForReadiness() {
        Repository repository = newRepository();
        long before = repository.head();

        repository.save(rowId, Repository.NO_STATE, Map.of("status", "draft"));

        assertThat(repository.head()).isEqualTo(before + 1);
    }

    /** The id every case works under, for an adapter's own tests that race two repositories. */
    protected final String id() {
        return rowId;
    }

    /**
     * Save at {@code expectedVersion} through {@code one} and {@code two} at the same instant, and return both
     * outcomes. Two repositories rather than one is how a real store's contention is reached: independent pools
     * racing for one row.
     */
    protected final List<SaveResult> race(Repository one, Repository two, int expectedVersion) throws Exception {
        try (ExecutorService pool = Executors.newFixedThreadPool(2)) {
            CountDownLatch start = new CountDownLatch(1);
            List<Future<SaveResult>> futures = new ArrayList<>();
            List<Repository> writers = List.of(one, two);
            for (int index = 0; index < writers.size(); index++) {
                Repository writer = writers.get(index);
                String name = index == 0 ? "one" : "two";
                futures.add(pool.submit(() -> {
                    start.await();
                    return writer.save(rowId, expectedVersion, Map.of("writer", name));
                }));
            }
            start.countDown();
            List<SaveResult> results = new ArrayList<>();
            for (Future<SaveResult> future : futures) {
                results.add(future.get(30, TimeUnit.SECONDS));
            }
            return results;
        }
    }
}
