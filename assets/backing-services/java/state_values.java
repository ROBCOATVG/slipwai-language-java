package com.example.deliverystarter.application.ports.state;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.jspecify.annotations.Nullable;

/**
 * What every adapter accepts as state: a JSON object of strings, booleans, finite numbers, nulls, lists and
 * nested objects — nothing a JSON column would store differently from how it was handed over.
 *
 * <p>The in-memory adapter keeps Java objects and SQL keeps text, so without this the fake would happily retain
 * an {@code Instant} or a {@code NaN} that Postgres would refuse or rewrite, and a slice that passed against the
 * fake would fail against the real store.
 */
public final class StateValues {

    private StateValues() {
    }

    /** Refuse anything that is not a finite, acyclic JSON object. */
    public static void requireJson(Map<String, Object> state) {
        check(state, Collections.newSetFromMap(new IdentityHashMap<>()));
    }

    /** A deep, unmodifiable copy, so neither side of the port can change what the other holds. */
    public static Map<String, Object> copyOf(Map<String, Object> state) {
        requireJson(state);
        return copyObject(state);
    }

    private static void check(@Nullable Object value, Set<Object> seen) {
        if (value == null || value instanceof String || value instanceof Boolean) {
            return;
        }
        if (value instanceof Double number && !Double.isFinite(number)
                || value instanceof Float single && !Float.isFinite(single)) {
            throw new IllegalArgumentException("state repository requires finite JSON numbers");
        }
        if (value instanceof Number) {
            return;
        }
        if (!(value instanceof Map<?, ?>) && !(value instanceof List<?>)) {
            throw new IllegalArgumentException(
                    "state repository requires JSON values, not " + value.getClass().getSimpleName());
        }
        if (!seen.add(value)) {
            throw new IllegalArgumentException("state repository requires acyclic JSON values");
        }
        if (value instanceof Map<?, ?> object) {
            for (Map.Entry<?, ?> entry : object.entrySet()) {
                if (!(entry.getKey() instanceof String)) {
                    throw new IllegalArgumentException("state repository requires JSON objects keyed by strings");
                }
                check(entry.getValue(), seen);
            }
        } else {
            for (Object item : (List<?>) value) {
                check(item, seen);
            }
        }
        seen.remove(value);
    }

    private static Map<String, Object> copyObject(Map<?, ?> object) {
        Map<String, Object> copied = new LinkedHashMap<>();
        object.forEach((key, item) -> copied.put((String) key, copy(item)));
        return Collections.unmodifiableMap(copied);
    }

    // A JSON null stays a null: the map is a LinkedHashMap rather than Map.copyOf for exactly that reason.
    @SuppressWarnings("NullAway")
    private static Object copy(@Nullable Object value) {
        if (value instanceof Map<?, ?> object) {
            return copyObject(object);
        }
        if (value instanceof List<?> list) {
            List<Object> copied = new ArrayList<>(list.size());
            list.forEach(item -> copied.add(copy(item)));
            return Collections.unmodifiableList(copied);
        }
        return value;
    }
}
