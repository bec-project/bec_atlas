from bec_atlas.model import Experiment
from bec_atlas.utils.migrations.migration_base import BaseMigration


class MigrateMongoAccounts(BaseMigration):
    """
    Migration to ensure experiment access_groups include the pgroup.
    Also cleans up null id fields from various collections.
    """

    def get_experiments(self) -> list[Experiment]:
        """
        Fetch experiments from MongoDB datasource.
        """
        experiments = self.datasource.find("experiments", {}, Experiment)
        return experiments

    def update_experiment(self, experiment: Experiment):
        """
        Update an experiment in MongoDB datasource.
        """
        access_groups = experiment.access_groups
        if experiment.pgroup in access_groups:
            return
        print(f"Updating experiment {experiment.id}")
        access_groups.append(experiment.pgroup)
        experiment.access_groups = access_groups
        self.datasource.patch(
            "experiments",
            experiment.id,
            {"access_groups": experiment.access_groups},
            dtype=Experiment,
        )

    def remove_null_ids(self):
        """
        Remove the id field from experiments collection where id is null. This is to clean up the data after the migration.
        """
        self.datasource.db["experiments"].update_many({"id": None}, {"$unset": {"id": ""}})
        self.datasource.db["realms"].update_many({"id": None}, {"$unset": {"id": ""}})
        self.datasource.db["deployments"].update_many({"id": None}, {"$unset": {"id": ""}})
        self.datasource.db["users"].update_many({"id": None}, {"$unset": {"id": ""}})
        self.datasource.db["user_credentials"].update_many({"id": None}, {"$unset": {"id": ""}})

    def run(self):
        """
        Execute the migration: update experiments and remove null ids.
        """
        experiments = self.get_experiments()
        for experiment in experiments:
            self.update_experiment(experiment)
        self.remove_null_ids()


if __name__ == "__main__":
    config = {"host": "localhost", "port": 27017}
    migrator = MigrateMongoAccounts(config=config)
    experiments = migrator.get_experiments()
    for experiment in experiments:
        migrator.update_experiment(experiment)

    migrator.remove_null_ids()
