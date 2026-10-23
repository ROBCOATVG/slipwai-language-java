package com.example.deliverystarter.seed;

import com.example.deliverystarter.adapters.driven.sql.Transactions;
import java.sql.Connection;
import java.sql.SQLException;
import java.sql.Savepoint;
import java.util.function.Supplier;

/**
 * The unit of work the seed door appends in: one JDBC connection, owned by one single-threaded process.
 *
 * <p>The service's own {@link Transactions} is the framework's — Spring's transaction manager or Quarkus's JTA —
 * and exists only inside a running application. The seed door is a command that exits, not the application, so
 * it hands {@code PostgresEventStore} this instead: the same port, kept by the one connection this process
 * opened. Nothing is bound to a thread — there is one connection and one caller, held in a field — which is how
 * "no {@code ThreadLocal} anywhere" stays true here as well. Nested work takes a savepoint, as the port asks,
 * and SERIALIZABLE is applied when the outermost transaction opens.
 *
 * <p>Not a bean, and not for the service: a second caller on a second thread would share this connection's
 * transaction. That is why it lives beside {@link SeedMain} rather than under {@code adapters/driven/sql}.
 */
final class SeedTransactions implements Transactions {

    private final Connection connection;
    private int depth;

    SeedTransactions(Connection connection) {
        this.connection = connection;
    }

    @Override
    public synchronized <T> T inTransaction(Isolation isolation, Supplier<T> work) {
        try {
            if (depth == 0) {
                connection.setAutoCommit(false);
                connection.setTransactionIsolation(isolation == Isolation.SERIALIZABLE
                        ? Connection.TRANSACTION_SERIALIZABLE
                        : Connection.TRANSACTION_READ_COMMITTED);
                return outermost(work);
            }
            return nested(work);
        } catch (SQLException failure) {
            throw Transactions.failed("run a unit of work", failure);
        }
    }

    @Override
    public synchronized boolean isActive() {
        return depth > 0;
    }

    @Override
    public synchronized <T> T onConnection(String what, SqlWork<T> work) {
        try {
            return work.run(connection);
        } catch (SQLException failure) {
            throw Transactions.failed(what, failure);
        }
    }

    private <T> T outermost(Supplier<T> work) throws SQLException {
        depth++;
        boolean committed = false;
        try {
            T result = work.get();
            // A commit Postgres refuses — a SERIALIZABLE transaction it could not order is refused here —
            // throws, and the finally below rolls back what is left.
            connection.commit();
            committed = true;
            return result;
        } finally {
            depth--;
            if (!committed) {
                connection.rollback();
            }
            connection.setAutoCommit(true);
        }
    }

    private <T> T nested(Supplier<T> work) throws SQLException {
        Savepoint savepoint = connection.setSavepoint();
        depth++;
        boolean kept = false;
        try {
            T result = work.get();
            connection.releaseSavepoint(savepoint);
            kept = true;
            return result;
        } finally {
            depth--;
            if (!kept) {
                connection.rollback(savepoint);
            }
        }
    }
}
