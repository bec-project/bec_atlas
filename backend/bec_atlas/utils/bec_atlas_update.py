import os

import typer

from bec_atlas.ingestor.deployment_ingestor import DeploymentIngestor
from bec_atlas.ingestor.proposal_ingestor import ProposalIngestor

app = typer.Typer(add_completion=False)


@app.command("deployments")
def update_deployments(file_path: str):
    """
    Update the available realms and deployments using the provided YAML file.
    """
    if not os.path.exists(file_path):
        typer.echo(f"File not found: {file_path}")
        raise typer.Exit(code=1)

    with open(file_path, "r") as f:
        data = f.read()
        # Process the YAML data
        typer.echo(f"Updating deployments with data from {file_path}")
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
