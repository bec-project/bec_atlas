import os
import time

import libtmux
from libtmux.exc import LibTmuxException


def activate_venv(pane, service_name, service_path):
    """
    Activate the python environment for a service.
    """

    # check if the current file was installed with pip install -e (editable mode)
    # if so, the venv is the service directory and it's called <service_name>_venv
    # otherwise, we simply take the currently running venv ;
    # in case of no venv, maybe it is running within a Conda environment

    if "site-packages" in __file__:
        venv_base_path = os.path.dirname(
            os.path.dirname(os.path.dirname(__file__.split("site-packages", maxsplit=1)[0]))
        )
        pane.send_keys(f"source {venv_base_path}/bin/activate")
        return
    if os.path.exists(f"{service_path}/{service_name}_venv"):
        pane.send_keys(f"source {service_path}/{service_name}_venv/bin/activate")
        return
    if os.getenv("CONDA_PREFIX"):
        pane.send_keys(f"conda activate {os.path.basename(os.environ['CONDA_PREFIX'])}")
        return


def tmux_start(bec_path: str, config_path: str, services: dict):
    """
    Launch the BEC server in a tmux session. All services are launched in separate panes.

    Args:
        bec_path (str): Path to the BEC source code
        config (str): Path to the config file
        services (dict): Dictionary of services to launch. Keys are the service names, values are path and command templates.

    """

    def get_new_session():
        tmux_server = libtmux.Server()
        session = tmux_server.new_session(
            "bec_atlas",
            window_name="BEC Atlas server. Use `ctrl+b d` to detach.",
            kill_session=True,
        )
        return session

    try:
        session = get_new_session()
    except LibTmuxException:
        # retry once... sometimes there is a hiccup in creating the session
        time.sleep(1)
        session = get_new_session()

    # create panes and run commands
    panes = []
    for ii, service_info in enumerate(services.items()):
        service, service_config = service_info

        if ii == 0:
            pane = session.attached_window.attached_pane
        else:
            pane = session.attached_window.split_window(vertical=False)
        panes.append(pane)

        activate_venv(
            pane,
            service_name=service,
            service_path=service_config["path"].substitute(base_path=bec_path),
        )

        if config_path:
            pane.send_keys(f"{service_config['command']} --config {config_path}")
        else:
            pane.send_keys(f"{service_config['command']}")
        session.attached_window.select_layout("tiled")

    session.mouse_all_flag = True
    session.set_option("mouse", "on")


def tmux_stop():
    """
    Stop the BEC server.
    """
    tmux_server = libtmux.Server()
    avail_sessions = tmux_server.sessions.filter(session_name="bec_atlas")
    if len(avail_sessions) != 0:
        # send ctrl+c to all panes
        for window in avail_sessions[0].windows:
            for pane in window.panes:
                pane.send_keys("C-c")
        avail_sessions[0].kill_session()
