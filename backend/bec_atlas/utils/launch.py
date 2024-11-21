import argparse
import os

import libtmux

from bec_atlas.utils.service_handler import ServiceHandler


def main():
    """
    Launch the BEC Atlas server in a tmux session. All services are launched in separate panes.
    """
    parser = argparse.ArgumentParser(description="Utility tool managing the BEC Atlas server")
    command = parser.add_subparsers(dest="command")
    start = command.add_parser("start", help="Start the BEC Atlas server")
    # start.add_argument(
    #     "--config", type=str, default=None, help="Path to the BEC service config file"
    # )
    # start.add_argument(
    #     "--no-tmux", action="store_true", default=False, help="Do not start processes in tmux"
    # )
    command.add_parser("stop", help="Stop the BEC Atlas server")
    restart = command.add_parser("restart", help="Restart the BEC Atlas server")
    command.add_parser("attach", help="Open the currently running BEC Atlas server session")

    args = parser.parse_args()
    try:
        # 'stop' has no config
        config = args.config
    except AttributeError:
        config = None

    service_handler = ServiceHandler(
        bec_path=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        config_path=config,
        no_tmux=args.no_tmux if "no_tmux" in args else False,
    )
    if args.command == "start":
        service_handler.start()
    elif args.command == "stop":
        service_handler.stop()
    elif args.command == "restart":
        service_handler.restart()
    elif args.command == "attach":
        server = libtmux.Server()
        session = server.find_where({"session_name": "bec_atlas"})
        if session is None:
            print("No BEC Atlas session found")
            return
        session.attach_session()


if __name__ == "__main__":
    main()
