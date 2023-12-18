# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT

import multiprocessing
import os
import tempfile
import time

import pytest
from libqtile import config, layout
from libqtile.backend.wayland.core import Core as WaylandCore
from libqtile.backend.x11.core import Core as X11Core
from libqtile.command.client import InteractiveCommandClient
from libqtile.confreader import Config
from libqtile.core.manager import Qtile
from libqtile.resources import default_config
from PySide6.QtWidgets import QApplication, QWidget
from pyvirtualdisplay.display import Display

from qtile_bonsai.layout import Bonsai


class BonsaiConfig(Config):
    auto_fullscreen = True
    groups = [
        config.Group("a"),
        config.Group("b"),
        config.Group("c"),
    ]
    layouts = [Bonsai(), layout.Columns(num_columns=3)]
    floating_layout = default_config.floating_layout
    keys = []
    mouse = []
    screens = [config.Screen()]
    follow_mouse_focus = False
    reconfigure_screens = False


# For now set to default of what headless wayland seems to default to. Need to figure
# out how to control this in wayland env.
test_display_resolution = (800, 600)


@pytest.fixture()
def qtile_x11():
    display = Display(backend="xvfb", size=test_display_resolution)
    display.start()

    def run_qtile():
        core = X11Core(display.new_display_var)
        qtile = Qtile(core, BonsaiConfig())
        qtile.loop()

    # launch qtile and give it some time to start up
    qtile_process = multiprocessing.Process(target=run_qtile)
    qtile_process.start()
    time.sleep(0.5)

    yield

    # terminate qtile and give it some time to do so
    qtile_process.terminate()
    time.sleep(0.5)

    display.stop()


@pytest.fixture()
def tmp_xdg_runtime_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture()
def qtile_wayland(tmp_xdg_runtime_dir):
    wlroots_env = {
        "WLR_BACKENDS": "headless",
        "WLR_LIBINPUT_NO_DEVICES": "1",
        "WLR_RENDERER": "pixman",
        "WLR_HEADLESS_OUTPUTS": "1",
        "XDG_RUNTIME_DIR": tmp_xdg_runtime_dir,
        "GDK_BACKEND": "wayland",
    }

    def run_qtile(queue):
        core = WaylandCore()
        qtile = Qtile(core, BonsaiConfig())
        queue.put(core.display_name)
        qtile.loop()

    # Prep wayland environment for our test qtile session
    os.environ.pop("DISPLAY", None)
    os.environ.update(wlroots_env)

    # launch qtile and give it some time to start up
    queue = multiprocessing.Queue()
    qtile_process = multiprocessing.Process(target=run_qtile, args=(queue,))
    qtile_process.start()
    time.sleep(0.5)

    # Update the environment with the appropriate wayland display value so subsequently
    # spawned applications can see it
    os.environ["WAYLAND_DISPLAY"] = queue.get()

    yield

    # terminate qtile and give it some time to do so
    qtile_process.terminate()
    time.sleep(0.5)

    os.environ.pop("WAYLAND_DISPLAY")


@pytest.fixture(params=["qtile_x11", "qtile_wayland"])
def manager(request):
    # pytest doesn't support auto-parametrizing fixtures yet but we can still invoke
    # them explicitly
    request.getfixturevalue(request.param)

    manager = InteractiveCommandClient()
    if manager.status() != "OK":
        raise RuntimeError("Test qtile instance did not respond with OK status")
    return manager


@pytest.fixture()
def make_window():
    window_processes = []

    def _make_window():
        def run_qt_app():
            app = QApplication([])
            window = QWidget()
            window.show()
            app.exec()

        process = multiprocessing.Process(target=run_qt_app)
        process.start()
        window_processes.append(process)

        # Give it some time to start up.
        time.sleep(0.5)

    yield _make_window

    for process in window_processes:
        process.terminate()

    # Give some time for windows to terminate
    time.sleep(0.5)


@pytest.fixture()
def spawn_test_window_cmd():
    return "python scripts/spawn_test_window.py"
