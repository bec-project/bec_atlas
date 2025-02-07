import os

import yaml


def load_env() -> dict:
    """
    Load the environment variables from the .env file.
    """
    env_file = "./.env.yaml"

    if not os.path.exists(env_file):
        env_file = os.path.join(os.path.dirname(__file__), ".env.yaml")

    if not os.path.exists(env_file):
        # check if there is an env file in the parent directory
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        env_file = os.path.join(current_dir, ".env.yaml")

    if not os.path.exists(env_file):
        # check if there is an env file in the deployment directory
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "deployment/.env.yaml")

    if not os.path.exists(env_file):
        raise FileNotFoundError(f"Could not find .env file in {os.getcwd()} or {current_dir}")

    with open(env_file, "r", encoding="utf-8") as file:
        yaml_config = yaml.safe_load(file)
    return yaml_config
