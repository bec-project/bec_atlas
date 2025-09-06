#!/usr/bin/env python3
"""
BEC Atlas Get Key - A utility to retrieve deployment environment files
"""
import getpass
import socket
from typing import Optional

import requests
import typer

app = typer.Typer(
    name="bec-atlas-get-key",
    help="Retrieve deployment environment file from BEC Atlas",
    add_completion=False,
)


def get_current_user() -> str:
    """Get the current system user."""
    return getpass.getuser()


def get_current_hostname() -> str:
    """Get the current hostname."""
    return socket.gethostname()


def prompt_password() -> str:
    """Securely prompt for password."""
    return typer.prompt("Password", hide_input=True)


@app.command()
def main(
    user: Optional[str] = typer.Option(
        None, "--user", "-u", help="Username for authentication (default: current user)"
    ),
    password: Optional[str] = typer.Option(
        None, "--password", "-p", help="Password for authentication (will prompt if not provided)"
    ),
    deployment: Optional[str] = typer.Option(
        None, "--deployment", "-d", help="Deployment name (default: current hostname)"
    ),
    base_url: str = typer.Option(
        "http://localhost", "--base-url", "-b", help="Base URL of the BEC Atlas API"
    ),
    output: str = typer.Option(
        ".env", "--output", "-o", help="Output file for the environment file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
) -> None:
    """
    Login to BEC Atlas and retrieve deployment environment file.

    This tool authenticates with the BEC Atlas API and downloads the environment
    file for a specified deployment. The environment file contains the necessary
    configuration to connect to the deployment.
    """
    # Set defaults
    if user is None:
        user = get_current_user()
        if verbose:
            typer.echo(f"Using current user: {user}")

    if deployment is None:
        deployment = get_current_hostname()
        if verbose:
            typer.echo(f"Using current hostname as deployment: {deployment}")

    if password is None:
        password = prompt_password()

    # Construct API URLs
    api_base = f"{base_url}/api/v1"
    login_url = f"{api_base}/user/login"
    env_url = f"{api_base}/deploymentCredentials/env"

    if verbose:
        typer.echo(f"API Base URL: {api_base}")
        typer.echo(f"Username: {user}")
        typer.echo(f"Deployment: {deployment}")
        typer.echo(f"Output file: {output}")

    try:
        # Step 1: Login
        if verbose:
            typer.echo("Logging in...")

        login_data = {"username": user, "password": password}
        login_response = requests.post(
            login_url, json=login_data, headers={"Content-Type": "application/json"}, timeout=30
        )

        if login_response.status_code != 200:
            typer.echo(
                f"Login failed with status {login_response.status_code}: {login_response.text}",
                err=True,
            )
            raise typer.Exit(1)

        # Extract token from response
        token = login_response.text.strip('"')  # Remove quotes if present

        if verbose:
            typer.echo("Login successful!")

        # Step 2: Get environment file
        if verbose:
            typer.echo(f"Retrieving environment file for deployment: {deployment}")

        headers = {"Authorization": f"Bearer {token}"}
        params = {"deployment_name": deployment}

        env_response = requests.get(env_url, headers=headers, params=params, timeout=30)

        if env_response.status_code != 200:
            typer.echo(
                f"Failed to retrieve environment file with status {env_response.status_code}: {env_response.text}",
                err=True,
            )
            raise typer.Exit(1)

        # Step 3: Save environment file
        try:
            with open(output, "w", encoding="utf-8") as f:
                f.write(env_response.text)

            typer.echo(f"Environment file saved to: {output}")

            if verbose:
                typer.echo("File contents:")
                typer.echo("-" * 40)
                typer.echo(env_response.text)
                typer.echo("-" * 40)

        except IOError as e:
            typer.echo(f"Failed to save environment file: {e}", err=True)
            raise typer.Exit(1)

    except requests.exceptions.RequestException as e:
        typer.echo(f"Network error: {e}", err=True)
        raise typer.Exit(1)
    except KeyboardInterrupt:
        typer.echo("\nOperation cancelled by user", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
