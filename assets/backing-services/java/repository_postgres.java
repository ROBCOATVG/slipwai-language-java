package com.example.deliverystarter.adapters.driven.repositorypostgres;

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
import javax.sql.DataSource;

/**
 * The state repository on Postgres: one statement per save, comparing and incrementing the version together.
 *
 * <p>A create is {@code INSERT … ON CONFLICT DO NOTHING}, an update is {@code UPDATE … WHERE version = ?}, and
 * each returns the new version or nothing. Two writers at one version cannot both win: the second waits on the
 * first's row lock, then finds the version moved or the key taken, and gets a conflict. No transaction is held
 * across the statement, which is why this takes the application's {@code DataSource} rather than the event
 * store's {@code Transactions} seam — a single statement is already atomic.
 *
 * <p>The schema is {@code V1__states.sql}, applied by {@code make migrate}.
 */
public final class PostgresRepository implements Repository {

    private static final String SELECT_ROW = "SELECT version, state::text FROM states WHERE id = ?";
    private static final String CREATE = "INSERT INTO states (id, version, state) VALUES (?, 0, ?::jsonb)"
            + " ON CONFLICT DO NOTHING RETURNING version";
    private static final String UPDATE = "UPDATE states SET state = ?::jsonb, version = version + 1"
            + " WHERE id = ? AND version = ? RETURNING version";
    private static final String COUNT = "SELECT count(*) FROM states";
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final TypeReference<Map<String, Object>> OBJECT = new TypeReference<>() { };

    private final DataSource dataSource;

    /** A repository over the application's own pool — Hikari under Spring Boot, Agroal under Quarkus. */
    public PostgresRepository(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public Optional<VersionedState> load(String id) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(SELECT_ROW)) {
            statement.setString(1, id);
            try (ResultSet row = statement.executeQuery()) {
                if (!row.next()) {
                    return Optional.empty();
                }
                return Optional.of(new VersionedState(id, row.getInt(1), decode(row.getString(2))));
            }
        } catch (SQLException failure) {
            throw new IllegalStateException("load state " + id, failure);
        }
    }

    @Override
    public SaveResult save(String id, int expectedVersion, Map<String, Object> state) {
        Repository.requireWritable(id, expectedVersion, state);
        String encoded = encode(state);
        boolean create = expectedVersion == NO_STATE;
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(create ? CREATE : UPDATE)) {
            if (create) {
                statement.setString(1, id);
                statement.setString(2, encoded);
            } else {
                statement.setString(1, encoded);
                statement.setString(2, id);
                statement.setInt(3, expectedVersion);
            }
            try (ResultSet row = statement.executeQuery()) {
                if (row.next()) {
                    return SaveResult.saved(row.getInt(1));
                }
            }
        } catch (SQLException failure) {
            throw new IllegalStateException("save state " + id, failure);
        }
        return SaveResult.versionConflict(load(id).map(VersionedState::version).orElse(NO_STATE));
    }

    @Override
    public long head() {
        try (Connection connection = dataSource.getConnection();
                Statement statement = connection.createStatement();
                ResultSet row = statement.executeQuery(COUNT)) {
            return row.next() ? row.getLong(1) : 0;
        } catch (SQLException failure) {
            throw new IllegalStateException("count states", failure);
        }
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
