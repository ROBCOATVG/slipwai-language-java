package com.example.deliverystarter.adapters.driven.repositorysqlite;

import com.example.deliverystarter.application.ports.state.Repository;
import com.example.deliverystarter.application.ports.state.SaveResult;
import com.example.deliverystarter.application.ports.state.VersionedState;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.Map;
import java.util.Optional;
import org.sqlite.SQLiteDataSource;

/**
 * The state repository on SQLite: one file, one connection, the same compare-and-swap as Postgres.
 *
 * <p>SQLite serialises writers, so the shared contract's guarantees hold here by construction and genuine
 * contention is proved on Postgres instead. The table is created on open — an embedded database has no
 * migration step — with the same shape as Postgres's {@code V1__states.sql}, the state as JSON text.
 */
public final class SqliteRepository implements Repository, AutoCloseable {

    private static final String SCHEMA = """
            CREATE TABLE IF NOT EXISTS states (
              id TEXT PRIMARY KEY,
              version INTEGER NOT NULL CHECK (version >= 0),
              state TEXT NOT NULL
            )""";
    private static final String SELECT_ROW = "SELECT version, state FROM states WHERE id = ?";
    private static final String CREATE =
            "INSERT INTO states (id, version, state) VALUES (?, 0, ?) ON CONFLICT DO NOTHING RETURNING version";
    private static final String UPDATE =
            "UPDATE states SET state = ?, version = version + 1 WHERE id = ? AND version = ? RETURNING version";
    private static final String COUNT = "SELECT count(*) FROM states";
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final TypeReference<Map<String, Object>> OBJECT = new TypeReference<>() { };

    private final Connection connection;

    /**
     * Open, or create, the repository at {@code location}: a file path, or {@code :memory:} for one that
     * lasts as long as the process — which is what the contract suite uses.
     */
    public SqliteRepository(String location) {
        SQLiteDataSource dataSource = new SQLiteDataSource();
        dataSource.setUrl("jdbc:sqlite:" + location);
        dataSource.setJournalMode("WAL");
        try {
            // One connection for the life of the adapter, for the event store's reason: a second connection to
            // ":memory:" would be a second, empty database.
            connection = dataSource.getConnection();
            try (Statement statement = connection.createStatement()) {
                statement.execute(SCHEMA);
            }
        } catch (SQLException failure) {
            throw new IllegalStateException("open state repository at " + location, failure);
        }
    }

    @Override
    public synchronized Optional<VersionedState> load(String id) {
        try (PreparedStatement statement = connection.prepareStatement(SELECT_ROW)) {
            statement.setString(1, id);
            try (ResultSet row = statement.executeQuery()) {
                if (!row.next()) {
                    return Optional.empty();
                }
                return Optional.of(new VersionedState(id, row.getInt("version"), decode(row.getString("state"))));
            }
        } catch (SQLException failure) {
            throw new IllegalStateException("load state " + id, failure);
        }
    }

    @Override
    public synchronized SaveResult save(String id, int expectedVersion, Map<String, Object> state) {
        Repository.requireWritable(id, expectedVersion, state);
        String encoded = encode(state);
        try {
            Optional<Integer> saved;
            if (expectedVersion == NO_STATE) {
                saved = returned(CREATE, statement -> {
                    statement.setString(1, id);
                    statement.setString(2, encoded);
                });
            } else {
                saved = returned(UPDATE, statement -> {
                    statement.setString(1, encoded);
                    statement.setString(2, id);
                    statement.setInt(3, expectedVersion);
                });
            }
            if (saved.isPresent()) {
                return SaveResult.saved(saved.get());
            }
            return SaveResult.versionConflict(load(id).map(VersionedState::version).orElse(NO_STATE));
        } catch (SQLException failure) {
            throw new IllegalStateException("save state " + id, failure);
        }
    }

    @Override
    public synchronized long head() {
        try (Statement statement = connection.createStatement();
                ResultSet row = statement.executeQuery(COUNT)) {
            return row.next() ? row.getLong(1) : 0;
        } catch (SQLException failure) {
            throw new IllegalStateException("count states", failure);
        }
    }

    @Override
    public synchronized void close() {
        try {
            connection.close();
        } catch (SQLException failure) {
            throw new IllegalStateException("close state repository", failure);
        }
    }

    private Optional<Integer> returned(String sql, Binder binder) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            binder.bind(statement);
            try (ResultSet row = statement.executeQuery()) {
                return row.next() ? Optional.of(row.getInt(1)) : Optional.empty();
            }
        }
    }

    /** One statement's parameters, which may throw the way JDBC does. */
    @FunctionalInterface
    private interface Binder {
        void bind(PreparedStatement statement) throws SQLException;
    }

    private static String encode(Map<String, Object> state) {
        try {
            return JSON.writeValueAsString(state);
        } catch (JsonProcessingException failure) {
            throw new IllegalArgumentException("state repository requires JSON values", failure);
        }
    }

    private static Map<String, Object> decode(String stored) {
        try {
            return JSON.readValue(stored, OBJECT);
        } catch (JsonProcessingException failure) {
            throw new IllegalStateException("stored state is not a JSON object", failure);
        }
    }
}
