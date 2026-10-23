package com.example.deliverystarter.application.ports.state;

/**
 * What a save came to. A lost race is a value rather than an exception, because it is an outcome the caller is
 * expected to handle — usually by loading the winner's row and deciding again.
 */
public sealed interface SaveResult {

    /** The row now stands at {@code version}. */
    record Saved(int version) implements SaveResult {
    }

    /**
     * Somebody else's decision won; the row stands at {@code actualVersion}, or {@link Repository#NO_STATE}
     * when there is no row at all.
     */
    record VersionConflict(int actualVersion) implements SaveResult {
    }

    static SaveResult saved(int version) {
        return new Saved(version);
    }

    static SaveResult versionConflict(int actualVersion) {
        return new VersionConflict(actualVersion);
    }
}
