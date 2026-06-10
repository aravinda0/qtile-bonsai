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

from qtile_bonsai import Bonsai


# For now set to default of what headless wayland seems to default to. Need to figure
# out how to control this in wayland env.
test_display_resolution = (800, 600)


def wait(seconds: float = 0.5):
    time.sleep(seconds)


@pytest.fixture()
def bonsai_layout(request):
    bonsai_config = getattr(request, "param", {})
    return Bonsai(**bonsai_config)


class TestConfigBase(Config):
    auto_fullscreen = True
    groups = [
        config.Group("a"),
        config.Group("b"),
        config.Group("c"),
    ]
    layouts = [layout.Columns(num_columns=3)]
    floating_layout = default_config.floating_layout
    keys = []
    mouse = []
    screens = [config.Screen()]
    follow_mouse_focus = False
    reconfigure_screens = False


@pytest.fixture()
def qtile_config(request, bonsai_layout):
    """Provides a qtile config parametrized by the `bonsai_layout` fixture OR allows for
    completely overriding the config via an indirect parametrized fixture (bypassing
    `bonsai_layout`).
    """

    class DefaultTestConfig(TestConfigBase):
        layouts = [bonsai_layout, layout.Columns(num_columns=3)]

    config = getattr(request, "param", DefaultTestConfig())

    return config


@pytest.fixture()
def qtile_x11(qtile_config):
    display = Display(backend="xvfb", size=test_display_resolution)
    display.start()

    def run_qtile():
        core = X11Core(display.new_display_var)
        qtile = Qtile(core, qtile_config)
        qtile.loop()

    # launch qtile and give it some time to start up
    qtile_process = multiprocessing.Process(target=run_qtile)
    qtile_process.start()
    wait(seconds=1)

    yield

    # terminate qtile and give it some time to do so
    qtile_process.terminate()
    wait()

    display.stop()


@pytest.fixture()
def tmp_xdg_runtime_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture()
def qtile_wayland(tmp_xdg_runtime_dir, qtile_config):
    wlroots_env = {
        "WLR_BACKENDS": "headless",
        "WLR_LIBINPUT_NO_DEVICES": "1",
        "WLR_RENDERER": "pixman",
        "WLR_HEADLESS_OUTPUTS": "1",
        "XDG_RUNTIME_DIR": tmp_xdg_runtime_dir,
        "GDK_BACKEND": "wayland",
        "QT_QPA_PLATFORM": "wayland",
    }

    def run_qtile(queue):
        from libqtile.backend.wayland.window import Internal
        from libqtile.command.base import expose_command

        def _enable_floating(self):
            if not self.floating:
                self.floating = True
                self.group.mark_floating(self, floating=True)

        def _disable_floating(self):
            if self.floating:
                self.floating = False
                self.group.mark_floating(self, floating=False)

        def _toggle_floating(self):
            if self.floating:
                _disable_floating(self)
            else:
                _enable_floating(self)

        def _enable_fullscreen(self):
            self.fullscreen = True
            self.group.layout_all()
            self.unhide()

        def _disable_fullscreen(self):
            self.fullscreen = False
            self.group.layout_all()

        def _toggle_fullscreen(self):
            if self.fullscreen:
                _disable_fullscreen(self)
            else:
                _enable_fullscreen(self)

        for command_name, command in {
            "enable_floating": _enable_floating,
            "disable_floating": _disable_floating,
            "toggle_floating": _toggle_floating,
            "enable_fullscreen": _enable_fullscreen,
            "disable_fullscreen": _disable_fullscreen,
            "toggle_fullscreen": _toggle_fullscreen,
        }.items():
            exposed_command = expose_command()(command)
            setattr(Internal, command_name, exposed_command)
            if not hasattr(Internal, "_commands"):
                Internal._commands = {
                    name: method
                    for cls in reversed(Internal.mro())
                    for name, method in cls.__dict__.items()
                    if hasattr(method, "_cmd")
                }
            Internal._commands[command_name] = exposed_command

        @expose_command()
        def create_test_window(self, *, floating=False):
            win = self.core.create_internal(0, 0, 100, 100)
            win.name = "test window"
            win.defunct = False
            win.wants_to_fullscreen = False
            win.fullscreen = False
            win.floating = floating
            win.minimized = False
            win.maximized = False
            win.has_focus = False
            win.float_x = None
            win.float_y = None
            win.can_steal_focus = True

            def match(_rule):
                return False

            def is_visible():
                return win.tree.node.enabled

            def has_user_set_position():
                return False

            def is_transient_for():
                return None

            def get_position():
                return win.x, win.y

            def get_size():
                return win._width, win._height

            win.match = match
            win.is_visible = is_visible
            win.has_user_set_position = has_user_set_position
            win.is_transient_for = is_transient_for
            win.get_position = get_position
            win.get_size = get_size
            win.get_pid = os.getpid
            self.current_group.add(win)
            return win.wid

        Qtile.create_test_window = create_test_window

        core = WaylandCore()
        qtile = Qtile(core, qtile_config)
        queue.put(core.display_name)
        qtile.loop()

    # Prep wayland environment for our test qtile session.
    saved_env = {
        key: os.environ.get(key)
        for key in (*wlroots_env, "DISPLAY", "WAYLAND_DISPLAY")
    }
    os.environ.pop("DISPLAY", None)
    os.environ.pop("WAYLAND_DISPLAY", None)
    os.environ.update(wlroots_env)

    # launch qtile and give it some time to start up
    queue = multiprocessing.Queue()
    qtile_process = multiprocessing.Process(target=run_qtile, args=(queue,))
    qtile_process.start()
    wait()

    # Update the environment with the display values for the test qtile session so
    # subsequently spawned applications can see it.
    os.environ["WAYLAND_DISPLAY"] = queue.get(timeout=5)

    yield

    # terminate qtile and give it some time to do so
    qtile_process.terminate()
    wait()

    for key, value in saved_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


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
def make_window(manager):
    window_processes = []

    def _make_window(*, floating: bool = False):
        if os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("DISPLAY"):
            manager.create_test_window(floating=floating)
            wait()
            return

        def run_qt_app():
            app = QApplication([])
            window = QWidget()
            if floating:
                # Set fixed aspect ratio so qtile's default `floating_layout` will
                # capture it without adding it to a tiled layout.
                window.setFixedSize(300, 200)
            window.show()
            app.exec()

        process = multiprocessing.Process(target=run_qt_app)
        process.start()
        window_processes.append(process)

        # Give it some time to start up.
        wait()

    yield _make_window

    for process in window_processes:
        process.terminate()

    # Give some time for windows to terminate
    wait()


@pytest.fixture()
def spawn_test_window_cmd():
    def _spawn_test_window_cmd(title: str = "test window"):
        if os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("DISPLAY"):
            return (
                "python -c \"from libqtile.command.client import "
                "InteractiveCommandClient; "
                "InteractiveCommandClient().create_test_window()\""
            )
        return f"python scripts/spawn_test_window.py {title}"

    return _spawn_test_window_cmd
