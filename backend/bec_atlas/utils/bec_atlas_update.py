import glob
import os

import typer
import yaml

from bec_atlas.ingestor.deployment_ingestor import DeploymentIngestor
from bec_atlas.ingestor.proposal_ingestor import ProposalIngestor

app = typer.Typer(add_completion=False)


@app.command("deployments")
def update_deployments(file_path: str = typer.Argument(None, help="Path to the YAML file")):
    """
    Update the available realms and deployments using the provided YAML file.
    If no path is specified, the deployment realms are used (deployment/realms/*.yaml)
    """
    if file_path is not None:
        if not os.path.exists(file_path):
            typer.echo(f"File not found: {file_path}")
            raise typer.Exit(code=1)
        files = [file_path]

    else:
        base_path = os.path.abspath(os.path.dirname(os.path.dirname((__file__))))
        realm_path = os.path.join(base_path, "deployment/realms/*.yaml")

        files = glob.glob(realm_path)

    for file in files:
        with open(file, "r") as f:
            data = yaml.safe_load(f)
            # Process the YAML data
            typer.echo(f"Updating deployments with data from {file}")
        DeploymentIngestor({"host": "localhost", "port": 27017}).load(data)


@app.command("experiments")
def update_experiments(
    duo_token: str = typer.Option(..., help="DUO API token"),
    full: bool = typer.Option(False, "--full", "-f", help="Full update of experiments"),
):
    """
    Update the available experiments with the information fetched from DUO.
    If `full` is set to True, a full update will be performed, otherwise only the experiments of
    the current year are fetched.
    """
    ingestor = ProposalIngestor(
        duo_token=duo_token, duo_base_url="https://duo.psi.ch/duo/api.php/v1"
    )
    typer.echo("Updating experiments from DUO")
    experiments = ingestor.load_proposals_from_duo(full=full)
    ingestor.ingest_to_mongo(experiments)


if __name__ == "__main__":
    app()
