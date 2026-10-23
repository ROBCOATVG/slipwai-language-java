package com.example.deliverystarter.seed;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.example.deliverystarter.adapters.driven.eventstorememory.InMemoryEventStore;
import com.example.deliverystarter.application.ports.events.CommittedEvent;
import com.example.deliverystarter.application.ports.events.EventStore;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * The seed door's rule, against the in-memory store: given events are appended once, a replay appends nothing,
 * and the refusals say what to do. {@code make seed-service} runs the same code against Postgres.
 */
class SeedTest {

    @TempDir
    Path directory;

    @Test
    void appendsWhatIsGivenOnceAndNothingOnAReplay() {
        EventStore store = new InMemoryEventStore();
        List<SeedMain.Given> given = List.of(
                new SeedMain.Given("order-1", "OrderPlaced", Map.of("orderId", "order-1", "total", 12)),
                new SeedMain.Given("order-1", "OrderPaid", Map.of("orderId", "order-1")));

        assertThat(SeedMain.seed(store, given, () -> Instant.EPOCH)).isEqualTo(new SeedMain.Seeded(2, 0));
        assertThat(SeedMain.seed(store, given, () -> Instant.EPOCH)).isEqualTo(new SeedMain.Seeded(0, 2));

        List<CommittedEvent> recorded = store.read("order-1");
        assertThat(recorded).extracting(CommittedEvent::type).containsExactly("OrderPlaced", "OrderPaid");
        assertThat(recorded).extracting(CommittedEvent::actor).containsOnly(SeedMain.SEED_ACTOR);
    }

    @Test
    void identityIgnoresKeyOrder() {
        Map<String, Object> forwards = new LinkedHashMap<>();
        forwards.put("a", 1);
        forwards.put("b", Map.of("y", 2, "x", 3));
        Map<String, Object> backwards = new LinkedHashMap<>();
        backwards.put("b", Map.of("x", 3, "y", 2));
        backwards.put("a", 1);

        assertThat(SeedMain.identity("s", "T", forwards)).isEqualTo(SeedMain.identity("s", "T", backwards));
        assertThat(SeedMain.identity("s", "T", forwards)).isNotEqualTo(SeedMain.identity("s", "U", forwards));
    }

    @Test
    void refusesToSeedWithoutTheDurableStore() throws IOException {
        Path file = write("[]");
        ByteArrayOutputStream err = new ByteArrayOutputStream();

        int code = SeedMain.run(new String[] {file.toString()}, null, stream(new ByteArrayOutputStream()),
                stream(err));

        assertThat(code).isEqualTo(2);
        assertThat(err.toString(StandardCharsets.UTF_8)).contains("DATABASE_URL is unset");
    }

    @Test
    void refusesAFileThatIsNotAListOfGivens() throws IOException {
        assertThatThrownBy(() -> SeedMain.read(write("{}"))).hasMessageContaining("is a list of");
        assertThatThrownBy(() -> SeedMain.read(write("[{\"event\": \"E\", \"data\": {}}]")))
                .hasMessageContaining("names no stream");
        assertThatThrownBy(() -> SeedMain.read(write("[{\"stream\": \"s\", \"event\": \"E\", \"data\": 1}]")))
                .hasMessageContaining("data is an object");
    }

    private Path write(String content) throws IOException {
        return Files.writeString(directory.resolve("given.json"), content);
    }

    private static PrintStream stream(ByteArrayOutputStream sink) {
        return new PrintStream(sink, true, StandardCharsets.UTF_8);
    }
}
