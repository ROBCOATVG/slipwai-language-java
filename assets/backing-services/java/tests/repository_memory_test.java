package com.example.deliverystarter.adapters.driven.repositorymemory;

import com.example.deliverystarter.application.ports.state.Repository;
import com.example.deliverystarter.repositorycontract.RepositoryContract;

/**
 * The contract, against the fake. Runs in {@code make verify} with no Docker, which is the whole reason the fake
 * exists; {@code make test-integration} runs the same contract against Postgres.
 */
class InMemoryRepositoryTest extends RepositoryContract {

    @Override
    protected Repository newRepository() {
        return new InMemoryRepository();
    }
}
