from unittest import mock

import mongomock
import pytest

from bec_atlas.utils.migrations.migration_base import BaseMigration
from bec_atlas.utils.migrations.migration_runner import MigrationRunner


class TestMigration001(BaseMigration):
    """Test migration 001."""

    def run(self):
        """Create a test collection."""
        self.datasource.db["test_collection"].insert_one({"data": "migration_001"})


class TestMigration002(BaseMigration):
    """Test migration 002."""

    def run(self):
        """Update the test collection."""
        self.datasource.db["test_collection"].insert_one({"data": "migration_002"})


class FailingTestMigration(BaseMigration):
    """Test migration that fails."""

    def run(self):
        """Intentionally fail."""
        raise RuntimeError("Migration failed intentionally")


@pytest.fixture
def mongo_client():
    """Create a mongomock client for testing."""
    client = mongomock.MongoClient()
    yield client
    client.close()


@pytest.fixture
def test_config(mongo_client):
    """Create a test configuration with mongomock client."""
    return {"host": "localhost", "port": 27017, "mongodb_client": mongo_client}


@pytest.fixture
def migration_runner(test_config):
    """Create a MigrationRunner instance for testing."""
    runner = MigrationRunner(config=test_config)
    with mock.patch.object(
        runner,
        "discover_migrations",
        return_value=[
            (1, "TestMigration001", TestMigration001),
            (2, "TestMigration002", TestMigration002),
            (998, "FailingTestMigration", FailingTestMigration),
        ],
    ):
        yield runner
    # Clean up the test database after each test
    runner.datasource.db.drop_collection(runner.MIGRATION_COLLECTION)
    runner.datasource.db.drop_collection("test_collection")


class TestMigrationRunner:
    """Test cases for MigrationRunner class."""

    def test_migration_index_created(self, migration_runner):
        """Test that migration index is created on initialization."""
        runner = migration_runner

        # Check that the index was created
        indexes = runner.datasource.db[runner.MIGRATION_COLLECTION].index_information()
        assert "migration_index_applied_at_idx" in indexes

    def test_record_migration_success(self, migration_runner):
        """Test recording a successful migration."""
        runner = migration_runner

        runner.record_migration(1, "TestMigration", success=True, comment="Test comment")

        # Verify the record was created
        collection = runner.datasource.db[runner.MIGRATION_COLLECTION]
        record = collection.find_one({"migration_index": 1})

        assert record is not None
        assert record["name"] == "TestMigration"
        assert record["success"] is True
        assert record["comment"] == "Test comment"
        assert "applied_at" in record

    def test_record_migration_failure(self, migration_runner):
        """Test recording a failed migration."""
        runner = migration_runner

        runner.record_migration(2, "FailedMigration", success=False, comment="Error message")

        # Verify the record was created
        collection = runner.datasource.db[runner.MIGRATION_COLLECTION]
        record = collection.find_one({"migration_index": 2})

        assert record is not None
        assert record["name"] == "FailedMigration"
        assert record["success"] is False
        assert record["comment"] == "Error message"

    def test_get_applied_migrations_empty(self, migration_runner):
        """Test getting applied migrations when none exist."""
        runner = migration_runner

        applied = runner.get_applied_migrations()

        assert applied == set()

    def test_get_applied_migrations_with_data(self, migration_runner):
        """Test getting applied migrations with existing data."""
        runner = migration_runner

        # Record some migrations
        runner.record_migration(1, "Migration1", success=True)
        runner.record_migration(2, "Migration2", success=True)
        runner.record_migration(3, "Migration3", success=False)

        applied = runner.get_applied_migrations()

        # Only successful migrations should be included
        assert applied == {1, 2}

    def test_get_pending_migrations_all_pending(self, migration_runner):
        """Test getting pending migrations when all are pending."""
        runner = migration_runner

        pending = runner.get_pending_migrations()

        # All discovered migrations should be pending
        all_migrations = runner.discover_migrations()
        assert len(pending) == len(all_migrations)

    def test_get_pending_migrations_some_applied(self, migration_runner):
        """Test getting pending migrations when some are already applied."""
        runner = migration_runner

        # Mark first migration as applied
        runner.record_migration(1, "Migration001", success=True)

        pending = runner.get_pending_migrations()
        all_migrations = runner.discover_migrations()

        # Should have one less pending migration
        assert len(pending) == len(all_migrations) - 1
        assert all(m[0] != 1 for m in pending)

    def test_run_migration_success(self, test_config):
        """Test running a successful migration."""
        runner = MigrationRunner(config=test_config)

        # Run a test migration
        runner.run_migration(999, "TestMigration001", TestMigration001)

        # Verify data was created
        assert runner.datasource.db["test_collection"].find_one({"data": "migration_001"})

        # Verify migration was recorded
        applied = runner.get_applied_migrations()
        assert 999 in applied

    def test_run_migration_failure(self, test_config):
        """Test running a migration that fails."""
        runner = MigrationRunner(config=test_config)

        # Run a failing migration
        with pytest.raises(RuntimeError, match="Migration failed intentionally"):
            runner.run_migration(998, "FailingTestMigration", FailingTestMigration)

        # Verify migration was recorded as failed
        collection = runner.datasource.db[runner.MIGRATION_COLLECTION]
        record = collection.find_one({"migration_index": 998})
        assert record is not None
        assert record["success"] is False
        assert "Migration failed intentionally" in record["comment"]

    def test_run_pending_migrations_none_pending(self, test_config):
        """Test running pending migrations when none are pending."""
        runner = MigrationRunner(config=test_config)

        # Mark all existing migrations as applied
        for idx, name, _ in runner.discover_migrations():
            runner.record_migration(idx, name, success=True)

        # Should complete without errors
        runner.run_pending_migrations()

        # No new migrations should be recorded
        pending = runner.get_pending_migrations()
        assert len(pending) == 0
