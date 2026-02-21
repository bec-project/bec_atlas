import os
import time

import libtmux
import psutil
from libtmux import Session
from libtmux.constants import PaneDirection
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
    # check if we are in a pyenv environment
    if os.getenv("PYENV_VERSION"):
        venv_name = os.getenv("PYENV_VIRTUAL_ENV", "").split(os.sep)[-1]
        if not venv_name:
            return
        pane.send_keys(f"pyenv activate {venv_name}")
        return


def get_new_session(tmux_session_name, window_label):

    tmux_server = libtmux.Server()

    session = None
    for _ in range(2):
        try:
            session = tmux_server.new_session(
                tmux_session_name,
                window_name=f"{window_label}. Use `ctrl+b d` to detach.",
                kill_session=True,
            )
        except LibTmuxException:
            # retry once... sometimes there is a hiccup in creating the session
            time.sleep(1)
            continue
        else:
            break
    return session


def tmux_start(
    bec_path: str,
    services: dict[str, "ServiceDesc"],
    tmux_session_name="bec_atlas",
    tmux_window_label="BEC Atlas Server",
    default_wait_after_start: float = 0.0,
):
    """
    Launch services in a tmux session. All services are launched in separate panes.

    Args:
        bec_path (str): Path to the BEC source code
        services (dict): Dictionary of services to launch. Keys are the service names, values are path and command templates.
        default_wait_after_start (float): Default time to wait (in seconds) after starting each service pane.

    """
    sessions: dict[str, Session] = {}
    ordered_services = list(enumerate(services.items()))
    ordered_services.sort(key=lambda item: (item[1][1].get("start_order", item[0]), item[0]))

    for _, (service, service_config) in ordered_services:
        if tmux_session_name not in sessions:
            session = get_new_session(tmux_session_name, tmux_window_label)
            pane = session.active_window.active_pane
            sessions[tmux_session_name] = session
        else:
            session = sessions[tmux_session_name]
            pane = session.active_window.split(direction=PaneDirection.Right)

        activate_venv(
            pane,
            service_name=service,
            service_path=service_config["path"].substitute(base_path=bec_path),
        )
        pane.cmd("select-pane", "-T", service)

        command = " ".join((service_config["command"], *service_config.get("args", [])))
        pane.send_keys(command)

        wait_after_start = service_config.get("wait_after_start", default_wait_after_start)
        if wait_after_start and wait_after_start > 0:
            time.sleep(wait_after_start)

    for session in sessions.values():
        session.active_window.select_layout("tiled")
        session.active_window.set_option("pane-border-status", "top")
        session.active_window.set_option("pane-border-format", " #{pane_title} ")
        session.mouse_all_flag = True
        session.set_option("mouse", "on")


def tmux_stop(timeout=5):
    """
    Stop the BEC server.
    """
    tmux_server = libtmux.Server()
    avail_sessions = tmux_server.sessions.filter(session_name="bec_atlas")

    if not avail_sessions:
        return

    session = avail_sessions[0]

    all_children = []
    for bash_pid in map(int, [p.pane_pid for p in session.panes]):
        try:
            parent_proc = psutil.Process(bash_pid)
            children = parent_proc.children(recursive=True)
            all_children.extend(children)
        except psutil.NoSuchProcess:
            continue

    # Send Ctrl+C to each pane
    for pane in session.panes:
        pane.send_keys("^C")  # sends SIGINT via tmux

    # Wait for processes to exit
    start_time = time.time()
    while time.time() - start_time < timeout:
        alive = [p for p in all_children if p.is_running()]
        if not alive:
            break
        time.sleep(0.1)

    # Kill remaining processes forcefully
    for proc in alive:
        try:
            proc.kill()
        except psutil.NoSuchProcess:
            pass

    # Kill tmux session
    try:
        session.kill_session()
    except LibTmuxException:
        # session may already exit itself if all panes are gone
        pass
