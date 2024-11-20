import sys
from string import Template

from bec_atlas.utils.tmux_launch import tmux_start, tmux_stop


class bcolors:
    """
    Colors for the terminal output.
    """

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class ServiceHandler:
    """
    Service handler for the BEC server. This class is used to start, stop and restart the BEC server.
    Depending on the platform, the server is launched in a tmux session or in an iTerm2 session.
    """

    SERVICES = {
        "fastapi-8000": {
            "path": Template("$base_path"),
            "command": "bec-atlas-fastapi --port 8000",
        },
        "fastapi-8001": {
            "path": Template("$base_path"),
            "command": "bec-atlas-fastapi --port 8001",
        },
        "redis": {"path": Template("$base_path"), "command": "redis-server --port 6380"},
    }

    def __init__(self, bec_path: str, config_path: str, no_tmux: bool = False):
        """

        Args:
            bec_path (str): Path to the BEC source code
            config_path (str): Path to the config file

        """
        self.bec_path = bec_path
        self.config_path = config_path
        self.no_tmux = no_tmux

        self._detect_available_interfaces()

    def _detect_available_interfaces(self):
        if self.no_tmux:
            self.interface = None
            return
        # check if we are on MacOS and if so, check if we have iTerm2 installed
        if sys.platform == "darwin":
            try:
                import iterm2
            except ImportError:
                self.interface = "tmux"
            else:
                self.interface = "iterm2"

        # if we are not on MacOS, we can only use tmux
        else:
            self.interface = "tmux"

    def start(self):
        """
        Start the BEC Atlas server using the available interface.
        """
        if self.interface == "tmux":
            print("Starting BEC Atlas server using tmux...")
            tmux_start(self.bec_path, self.config_path, self.SERVICES)
            print(
                f"{bcolors.OKCYAN}{bcolors.BOLD}Use `bec-atlas attach` to attach to the BEC Atlas server. Once connected, use `ctrl+b d` to detach again.{bcolors.ENDC}"
            )
        elif self.interface == "iterm2":
            pass
        else:
            # no tmux
            raise ValueError("No valid interface available")

    def stop(self):
        """
        Stop the BEC server using the available interface.
        """
        print("Stopping BEC Atlas server...")
        if self.interface == "tmux":
            tmux_stop()
        elif self.interface == "iterm2":
            pass
        else:
            # no tmux
            raise ValueError("No valid interface available")

    def restart(self):
        """
        Restart the BEC Atlas server using the available interface.
        """
        print("Restarting BEC Atlas server...")
        self.stop()
        self.start()
