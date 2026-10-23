-- The state-stored write model's one table: the current state per id, and the version that guards it.
--
-- Mutable by design, unlike `events`: a save replaces the row, and the version is what makes the replacement
-- safe. The adapter compares and increments it in one statement, so two writers at one version cannot both
-- win. The state is a JSON object, checked here as well as in the port, because a row outlives the code that
-- wrote it.
CREATE TABLE states (
  id       TEXT    PRIMARY KEY,
  version  INTEGER NOT NULL CHECK (version >= 0),
  state    JSONB   NOT NULL CHECK (jsonb_typeof(state) = 'object')
);
