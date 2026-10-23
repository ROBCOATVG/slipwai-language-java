package com.example.deliverystarter.application.ports.state;

import java.util.Map;

/**
 * One loaded row: its id, the version a save has to name to replace it, and the state itself.
 *
 * <p>The state is a deep, unmodifiable copy, so a caller that edits what it loaded is editing nothing the store
 * holds — the decision it makes has to go back through {@link Repository#save}.
 */
public record VersionedState(String id, int version, Map<String, Object> state) {

    public VersionedState {
        state = StateValues.copyOf(state);
    }
}
