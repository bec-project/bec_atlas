import importlib
import inspect
import logging
from datetime import datetime
from pathlib import Path
from typing import Type

from pymongo import ASCENDING

from bec_atlas.datasources.mongodb.mongodb import MongoDBDatasource
from bec_atlas.model import MongoDBMigrateModel
from bec_atlas.utils.migrations.migration_base import BaseMigration

logger = logging.getLogger(__name__)


class MigrationRunner:
    """
    MigrationRunner manages and executes database migrations.

    It tracks which migrations have been applied and runs pending migrations
    in the order they are discovered. Migration history is stored in MongoDB
    with a combined index for efficient querying.
    """

    MIGRATION_COLLECTION = "migrations"

    def __init__(self, config: dict):
        self.config = config
        self.datasource = MongoDBDatasource(config=self.config)
        self.datasource.connect(include_setup=False)
        self._ensure_migration_index()

    def _ensure_migration_index(self):
        """
        Create a combined index on the migrations collection.

        The index is on (migration_index, applied_at) fields to efficiently query
        migration history and prevent duplicate migration runs.
        """
        collection = self.datasource.db[self.MIGRATION_COLLECTION]

        # Create combined index on migration_index and applied_at
        collection.create_index(
            [("migration_index", ASCENDING), ("applied_at", ASCENDING)],
            name="migration_index_applied_at_idx",
            unique=False,
        )

        logger.info("Migration indexes ensured")

    def get_applied_migrations(self) -> set[int]:
        """
        Get the set of migration indexes that have been successfully applied.

        Returns:
            set[int]: Set of migration indexes that completed successfully
        """
        collection = self.datasource.db[self.MIGRATION_COLLECTION]

        # Get all successful migrations with only the migration_index field
        applied = collection.find({"success": True}, {"migration_index": 1})
        return {doc["migration_index"] for doc in applied}

    def record_migration(
        self, migration_index: int, name: str, success: bool, comment: str | None = None
    ) -> None:
        """
        Record a migration execution in the database.

        Args:
            migration_index: Numeric index of the migration (e.g., 001)
            name: Name of the migration
            success: Whether the migration succeeded
            comment: Optional comment about the migration execution
        """
        migration_record = MongoDBMigrateModel(
            migration_index=migration_index,
            name=name,
            applied_at=datetime.now().isoformat(),
            success=success,
            comment=comment,
        )

        collection = self.datasource.db[self.MIGRATION_COLLECTION]
        collection.insert_one(migration_record.model_dump(by_alias=True, exclude={"id"}))

        status = "succeeded" if success else "failed"
        logger.info(f"Migration {name} {status}")

    def discover_migrations(self) -> list[tuple[int, str, Type[BaseMigration]]]:
        """
        Discover all migration classes in the pipelines directory.

        Scans for all .py files (excluding __init__.py) and extracts migration
        classes. Files should be named with 3-digit prefix (e.g., 001_*.py).

        Args:
            migrations_module: Python module path to search for migrations

        Returns:
            list[tuple[int, str, Type[BaseMigration]]]: List of tuples (index, name, class)
            sorted by index
        """
        migrations = []

        pipelines_dir = Path(__file__).parent / "pipelines"
        module_name = "bec_atlas.utils.migrations.pipelines"

        try:

            # Find all Python files except __init__.py
            for py_file in sorted(pipelines_dir.glob("*.py")):
                if py_file.name == "__init__.py":
                    continue

                # Extract migration index from filename (first 3 digits)
                try:
                    migration_index = int(py_file.name[:3])
                except ValueError:
                    logger.warning(f"Skipping {py_file.name}: filename must start with 3 digits")
                    continue

                migration_module_name = f"{module_name}.{py_file.stem}"

                try:
                    migration_module = importlib.import_module(migration_module_name)

                    # Find all classes in the module
                    for name, obj in inspect.getmembers(migration_module, inspect.isclass):
                        # Check if it's a migration class
                        if (
                            issubclass(obj, BaseMigration)
                            and obj is not BaseMigration
                            and not inspect.isabstract(obj)
                        ):
                            migrations.append((migration_index, obj.__name__, obj))
                            logger.debug(
                                f"Discovered migration {migration_index:03d}: {obj.__name__}"
                            )
                            break  # Only one migration class per file

                except Exception as e:
                    logger.warning(f"Failed to import {migration_module_name}: {e}")

        except Exception as e:
            logger.error(f"Failed to discover migrations in {module_name}: {e}")

        # Sort migrations by numeric index
        migrations.sort(key=lambda m: m[0])
        return migrations

    def get_pending_migrations(self) -> list[tuple[int, str, Type[BaseMigration]]]:
        """
        Get list of migrations that haven't been applied yet.
        If a newer migration has been applied but an older one hasn't, the older one will not be included
        in the pending list since it should be run first to maintain migration order and integrity.

        Returns:
            list[tuple[int, str, Type[BaseMigration]]]: List of pending migrations
        """
        all_migrations = self.discover_migrations()
        applied_indexes = self.get_applied_migrations()
        min_applied_index = min(applied_indexes) if applied_indexes else 0

        skipped = [
            m for m in all_migrations if m[0] in applied_indexes and m[0] < min_applied_index
        ]
        if skipped:
            raise RuntimeError(
                f"Cannot run pending migrations because the following older migrations have been applied: "
                f"{', '.join(f'{m[0]:03d} {m[1]}' for m in skipped)}. Please run these migrations first to maintain order."
            )

        # Note: migrations are already sorted by index, so this will maintain order of pending migrations
        pending = [m for m in all_migrations if m[0] not in applied_indexes]

        logger.info(
            f"Found {len(all_migrations)} total migrations, "
            f"{len(applied_indexes)} applied, {len(pending)} pending"
        )

        return pending

    def run_migration(
        self, migration_index: int, migration_name: str, migration_class: Type[BaseMigration]
    ) -> None:
        """
        Execute a single migration.

        Args:
            migration_index: Numeric index of the migration
            migration_name: Name of the migration class
            migration_class: The migration class to instantiate and run

        """
        logger.info(f"Running migration {migration_index:03d}: {migration_name}")

        try:
            migration = migration_class(config=self.config)
            migration.run()

            # Record successful migration
            metadata = migration.get_metadata()
            comment = metadata.get("description", "").strip()
            self.record_migration(migration_index, migration_name, success=True, comment=comment)

            logger.info(f"Migration {migration_index:03d} completed successfully")
            return

        except Exception as exc:
            error_msg = f"Error: {str(exc)}"
            logger.error(f"Migration {migration_index:03d} failed: {error_msg}")

            # Record failed migration
            self.record_migration(migration_index, migration_name, success=False, comment=error_msg)
            raise exc

    def run_pending_migrations(self) -> None:
        """
        Run all pending migrations.
        """
        pending = self.get_pending_migrations()

        if not pending:
            logger.info("No pending migrations to run")
            return

        logger.info(f"Starting execution of {len(pending)} pending migrations")

        for migration_index, migration_name, migration_class in pending:
            self.run_migration(migration_index, migration_name, migration_class)


def launch():  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    config = {"host": "localhost", "port": 27017}
    runner = MigrationRunner(config=config)
    runner.run_pending_migrations()


if __name__ == "__main__":  # pragma: no cover
    config = {"host": "localhost", "port": 27017}
    runner = MigrationRunner(config=config)

    # Run all pending migrations
    runner.run_pending_migrations()
