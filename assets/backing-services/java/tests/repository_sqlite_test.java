package com.example.deliverystarter.adapters.driven.repositorysqlite;

import static org.assertj.core.api.Assertions.assertThat;

import com.example.deliverystarter.application.ports.state.Repository;
import com.example.deliverystarter.application.ports.state.SaveResult;
import com.example.deliverystarter.repositorycontract.RepositoryContract;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * The shared contract against SQLite, plus the one thing only a file-backed store can prove. Runs in
 * {@code make verify}: an embedded database needs nothing started and nothing migrated.
 */
class SqliteRepositoryTest extends RepositoryContract {

    private final List<SqliteRepository> opened = new ArrayList<>();

    @TempDir
    Path directory;

    @Override
    protected Repository newRepository() {
        SqliteRepository repository = new SqliteRepository(":memory:");
        opened.add(repository);
        return repository;
    }

    @AfterEach
    void close() {
        opened.forEach(SqliteRepository::close);
    }

    /** The whole reason to choose SQLite over the in-memory adapter. */
    @Test
    void keepsTheRowAndItsVersionAcrossACloseAndReopen() {
        String location = directory.resolve("states.sqlite3").toString();
        try (SqliteRepository first = new SqliteRepository(location)) {
            first.save("order-1", Repository.NO_STATE, Map.of("status", "draft"));
        }

        try (SqliteRepository reopened = new SqliteRepository(location)) {
            assertThat(reopened.load("order-1").orElseThrow().version()).isZero();
            // A caller that has not noticed the restart is still refused, by the same rule as before it.
            assertThat(reopened.save("order-1", Repository.NO_STATE, Map.of("status", "raced")))
                    .isEqualTo(SaveResult.versionConflict(0));
        }
    }
}
