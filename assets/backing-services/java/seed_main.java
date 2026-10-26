package com.example.deliverystarter.seed;

import com.example.deliverystarter.adapters.driven.eventstorepostgres.PostgresEventStore;
import com.example.deliverystarter.application.ports.events.Actor;
import com.example.deliverystarter.application.ports.events.AppendResult;
import com.example.deliverystarter.application.ports.events.CommittedEvent;
import com.example.deliverystarter.application.ports.events.CorrelationId;
import com.example.deliverystarter.application.ports.events.DomainEvent;
import com.example.deliverystarter.application.ports.events.EventStore;
import com.example.deliverystarter.application.ports.events.EventStoreException;
import com.example.deliverystarter.config.DatabaseUrl;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.function.Supplier;
import org.jspecify.annotations.Nullable;

/**
 * The seed door: append the events a slice's {@code try-it.json} <em>gives</em>, through this service's own
 * event-store port.
 *
 * <pre>
 * make seed-service FILE=given.json
 * cd apps/service
 * DATABASE_URL=postgres://app:app@localhost:5433/app \
 *     ./mvnw -B -q -DskipTests compile exec:java@seed -Dexec.args=$PWD/given.json
 * </pre>
 *
 * <p>The file is a list of {@code {"stream", "event", "data"}} — the events a story needs that the slice which
 * would have written them has not been built yet, so a view can be seeded to a state and judged before its
 * producers exist. They go in the way every event goes in: through the port, at the stream's current version,
 * each written by a system actor under one correlation id per run. Never through an HTTP route — this is a
 * process with the store's credentials, and the app serves no door.
 *
 * <p><strong>A replay records nothing twice.</strong> An event's identity here is the hash of its stream, its
 * type and its data; one already on the stream with the same identity is skipped, so seeding the same stories
 * into the same database again adds nothing. <strong>It needs the durable store</strong>: with no
 * {@code DATABASE_URL} there is no log to append to, and this says so and exits 2 rather than seeding an
 * in-memory store the next process would never see.
 */
public final class SeedMain {

    /** Who wrote a seeded event: system work names itself, and a seeded fact is one no person decided. */
    static final Actor SEED_ACTOR = new Actor("system", "systems/seed-door");

    // Sorted keys at every depth, so the same data hashes the same whichever order a file or the store wrote it in.
    private static final ObjectMapper JSON =
            new ObjectMapper().configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);

    private SeedMain() {
    }

    /** One event a story gives. {@code slice} is carried by the file for its reader and not used here. */
    record Given(String stream, String event, Map<String, Object> data) {
    }

    /** What a run came to. */
    record Seeded(int appended, int skipped) {
    }

    /** The exit code is this command's interface: 2 is the refusal `make` and slipwai read. */
    public static void main(String[] args) {
        System.exit(run(args, System.getenv("DATABASE_URL"), System.out, System.err));
    }

    /** The command with its edges handed in, so a test can drive every refusal without a database. */
    static int run(String[] args, @Nullable String databaseUrl, PrintStream out, PrintStream err) {
        if (args.length != 1) {
            err.println("seed: give the file of events to append — make seed-<service> FILE=<json>");
            return 1;
        }
        if (databaseUrl == null || databaseUrl.isBlank()) {
            err.println("seed: DATABASE_URL is unset, so there is no durable store to append to. The seed door "
                    + "needs the database `make services-up` starts; an in-memory store would be gone before the "
                    + "app read it.");
            return 2;
        }
        try {
            List<Given> given = read(Path.of(args[0]));
            DatabaseUrl database = DatabaseUrl.parse(databaseUrl);
            try (Connection connection = DriverManager.getConnection(
                    database.jdbcUrl(), database.username(), database.password())) {
                EventStore store = new PostgresEventStore(new SeedTransactions(connection));
                Seeded seeded = seed(store, given, Instant::now);
                out.println("seed: " + seeded.appended() + " event(s) appended, " + seeded.skipped()
                        + " already there");
                return 0;
            }
        } catch (IOException | SQLException | EventStoreException | IllegalArgumentException
                | IllegalStateException failure) {
            err.println("seed: " + failure.getMessage());
            return 1;
        }
    }

    /** Parse the file a story's givens were written to, refusing anything that is not one. */
    static List<Given> read(Path path) throws IOException {
        JsonNode parsed = JSON.readTree(Files.readString(path, StandardCharsets.UTF_8));
        if (parsed == null || !parsed.isArray()) {
            throw new IllegalArgumentException(path + " is a list of { stream, event, data }");
        }
        List<Given> given = new ArrayList<>();
        int index = 0;
        for (JsonNode one : parsed) {
            index++;
            JsonNode stream = one.get("stream");
            JsonNode event = one.get("event");
            JsonNode data = one.get("data");
            if (stream == null || !stream.isTextual() || stream.asText().isBlank()) {
                throw new IllegalArgumentException("given " + index + " names no stream");
            }
            if (event == null || !event.isTextual() || event.asText().isBlank()) {
                throw new IllegalArgumentException("given " + index + " names no event");
            }
            if (data == null || !data.isObject()) {
                throw new IllegalArgumentException("given " + index + "'s data is an object in the model's shape");
            }
            @SuppressWarnings("unchecked")
            Map<String, Object> payload = JSON.convertValue(data, Map.class);
            given.add(new Given(stream.asText(), event.asText(), payload));
        }
        return given;
    }

    /**
     * Append each given event that is not already on its stream, at the stream's current version. Against the
     * port rather than the adapter, so the rule is tested on the in-memory store.
     */
    static Seeded seed(EventStore store, List<Given> given, Supplier<Instant> now) {
        CorrelationId correlation = new CorrelationId(UUID.randomUUID());
        int appended = 0;
        int skipped = 0;
        for (Given one : given) {
            List<CommittedEvent> existing = store.read(one.stream());
            Set<String> held = new HashSet<>();
            for (CommittedEvent event : existing) {
                held.add(identity(event.streamId(), event.type(), event.payload()));
            }
            if (held.contains(identity(one.stream(), one.event(), one.data()))) {
                skipped++;
                continue;
            }
            DomainEvent event = new DomainEvent(one.event(), 1, one.stream(), one.data(),
                    now.get().toString(), SEED_ACTOR, correlation);
            AppendResult result = store.append(one.stream(), EventStore.currentVersion(existing), List.of(event));
            if (result instanceof AppendResult.VersionConflict conflict) {
                throw new IllegalStateException(one.event() + " on " + one.stream() + " was not appended: the "
                        + "stream moved to version " + conflict.actualVersion() + " while this ran. Run it again.");
            }
            appended++;
        }
        return new Seeded(appended, skipped);
    }

    /** The identity a replay is recognised by: the hash of stream, type and canonical data. */
    static String identity(String stream, String type, Map<String, Object> data) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            String canonical = stream + '\u0000' + type + '\u0000' + JSON.writeValueAsString(data);
            return HexFormat.of().formatHex(digest.digest(canonical.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException | JsonProcessingException failure) {
            throw new IllegalStateException("hash a given event", failure);
        }
    }
}
