# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


import itertools
import re
from typing import Callable

from libqtile.backend.base import Window
from libqtile.config import ScreenRect
from libqtile.layout.base import Layout
from libqtile.log_utils import logger

from qtile_bonsai.core.tree import (
    Axis,
    Pane,
    Tab,
    Tree,
    TreeEvent,
)
from qtile_bonsai.theme import Gruvbox
from qtile_bonsai.tree import BonsaiNodeMixin, BonsaiPane, BonsaiTree


class Bonsai(Layout):
    level_specific_config_format = re.compile(r"^L(\d+)\.(.+)")
    defaults = [
        (
            "window.margin",
            0,
            "Size of the margin space around windows",
        ),
        (
            "window.border_size",
            1,
            "Width of the border around windows",
        ),
        (
            "window.border_color",
            Gruvbox.darker_yellow,
            "Color of the border around windows",
        ),
        (
            "window.active.border_color",
            Gruvbox.dark_yellow,
            "Color of the border around an active window",
        ),
        (
            "tab_bar.height",
            20,
            "Height of tab bars",
        ),
        (
            "tab_bar.hide_when",
            "single_tab",
            """
            When to hide the tab bar. Allowed values are 'never', 'always',
            'single_tab'.

            When 'single_tab' is configured, the bar is not shown whenever there is a
            lone tab remaining, but shows up again when another tab is added. 

            For nested tab levels, configuring 'always' or 'single_tab' actually means
            that when only a single tab remains, its contents get 'merged' upwards,
            eliminating the sub-tab level.
            """,
        ),
        (
            "tab_bar.margin",
            0,
            "Size of the margin space around tab bars",
        ),
        (
            "tab_bar.border_size",
            0,
            "Size of the border around tab bars",
        ),
        (
            "tab_bar.border_color",
            Gruvbox.dark_yellow,
            "Color of border around tab bars",
        ),
        (
            "tab_bar.bg_color",
            Gruvbox.bg0,
            "Background color of tab bars, beind their tabs",
        ),
        ("tab_bar.tab.min_width", 50, "Minimum width of a tab on a tab bar"),
        ("tab_bar.tab.margin", 0, "Size of the margin space around individual tabs"),
        ("tab_bar.tab.padding", 20, "Size of the padding space inside individual tabs"),
        (
            "tab_bar.tab.bg_color",
            Gruvbox.bg1,
            "Background color of individual tabs",
        ),
        (
            "tab_bar.tab.fg_color",
            Gruvbox.fg1,
            "Foreground text color of individual tabs",
        ),
        ("tab_bar.tab.font_family", "Mono", "Font family to use for tab titles"),
        ("tab_bar.tab.font_size", 15, "Font size to use for tab titles"),
        (
            "tab_bar.tab.active.bg_color",
            Gruvbox.bg4,
            "Background color of active tabs",
        ),
        (
            "tab_bar.tab.active.fg_color",
            Gruvbox.fg1,
            "Foreground text color of the active tab",
        ),
    ]

    def __init__(self, **config) -> None:
        super().__init__(**config)
        self.add_defaults(self.defaults)

        self._tree: Tree
        self._focused_window: Window
        self._windows_to_panes: dict[Window, BonsaiPane]
        self._on_next_window: Callable[[], BonsaiPane]

        self._reset()

    @property
    def focused_window(self) -> Window:
        return self._focused_window

    @property
    def focused_pane(self) -> Pane:
        return self._windows_to_panes[self.focused_window]

    def clone(self, group):
        """In the manner qtile expects, creates a fresh, blank-slate instance of this
        class. `Group` instances will invoke this to get fresh, unique instance of this
        layout for themselves.

        This is a bit different from traditional copying/cloning of any 'current' state
        of the layout instance. In qtile, the config file holds the 'first' instance of
        the layout, then each Group instance 'clones' of that original instance (which
        likely remains in its initial state) and uses the new instance for all future
        operations.
        """
        pseudo_clone = super().clone(group)
        pseudo_clone._reset()
        return pseudo_clone

    def layout(self, windows: list[Window], screen_rect: ScreenRect):
        """Handles window layout based on the internal tree representation.

        Unlike the base class implementation, this does not invoke `Layout.configure()`
        for each window, as there are other elements such as tab-bar panels to process
        as well.
        """
        for node in self._tree.iter_walk():
            if self._tree.is_visible(node):
                node.render(screen_rect, self._tree)
            else:
                node.hide()

    def configure(self, window: Window, screen_rect: ScreenRect):
        """Defined since this is an abstract method, but not implemented since things
        are handled in `self.layout()`.
        """
        raise NotImplementedError

    def add(self, window: Window):
        if self._tree.is_empty:
            self._on_next_window = self._handle_default_next_window

        pane = self._on_next_window()
        pane.window = window

        self._windows_to_panes[window] = pane

    def remove(self, window: Window) -> Window | None:
        pane = self._windows_to_panes[window]
        next_focus_pane = self._tree.remove(pane)
        del self._windows_to_panes[window]
        if next_focus_pane is not None:
            return next_focus_pane.window
        return None

    def focus(self, window: Window):
        self._focused_window = window
        self._tree.focus(self.focused_pane)

    def focus_first(self) -> Window | None:
        first = next(self._tree.iter_panes(), None)
        if first is not None:
            return first.window
        return None

    def focus_last(self) -> Window | None:
        panes = list(self._tree.iter_panes())
        if panes:
            return panes[-1].window
        return None

    def focus_next(self, window) -> Window | None:
        current_pane = self._windows_to_panes[window]
        panes = list(self._tree.iter_panes())
        i = panes.index(current_pane)
        if i != len(panes) - 1:
            return panes[i + 1].window
        return None

    def focus_previous(self, window) -> Window | None:
        current_pane = self._windows_to_panes[window]
        panes = list(self._tree.iter_panes())
        i = panes.index(current_pane)
        if i != 0:
            return panes[i - 1].window
        return None

    def show(self, screen_rect: ScreenRect):
        width_changed = screen_rect.width != self._tree.width
        height_changed = screen_rect.height != self._tree.height
        if width_changed or height_changed:
            self._tree.reset_dimensions(screen_rect.width, screen_rect.height)

    def hide(self):
        # While other layouts are active, ensure that any new windows are captured
        # consistenty with the default tab layout here.
        self._on_next_window = self._handle_default_next_window

        self._hide_all_internal_windows()

    def cmd_next(self):
        next_window = self.focus_next(self.focused_window)
        if next_window is not None:
            self._request_focus(self._windows_to_panes[next_window])

    def cmd_previous(self):
        prev_window = self.focus_previous(self.focused_window)
        if prev_window is not None:
            self._request_focus(self._windows_to_panes[prev_window])

    def cmd_spawn_split(self, program: str, axis: Axis, ratio: float = 0.5):
        if self._tree.is_empty:
            logger.warn("There are no windows yet to split")
            return

        def _handle_next_window():
            return self._tree.split(self.focused_pane, axis, ratio)

        self._on_next_window = _handle_next_window

        self.group.qtile.cmd_spawn(program)

    def cmd_spawn_tab(
        self, program: str, *, new_level: bool = False, level: int | None = None
    ):
        def _handle_next_window():
            return self._tree.tab(self.focused_pane, new_level=new_level, level=level)

        self._on_next_window = _handle_next_window

        self.group.qtile.cmd_spawn(program)

    def cmd_left(self, *, wrap: bool = True):
        if self._tree.is_empty:
            return

        next_pane = self._tree.left(self.focused_pane, wrap=wrap)
        self._request_focus(next_pane)

    def cmd_right(self, *, wrap: bool = True):
        if self._tree.is_empty:
            return

        next_pane = self._tree.right(self.focused_pane, wrap=wrap)
        self._request_focus(next_pane)

    def cmd_up(self, *, wrap: bool = True):
        if self._tree.is_empty:
            return

        next_pane = self._tree.up(self.focused_pane, wrap=wrap)
        self._request_focus(next_pane)

    def cmd_down(self, *, wrap: bool = True):
        if self._tree.is_empty:
            return

        next_pane = self._tree.down(self.focused_pane, wrap=wrap)
        self._request_focus(next_pane)

    def cmd_next_tab(self, *, wrap: bool = True):
        if self._tree.is_empty:
            return

        next_pane = self._tree.next_tab(self.focused_pane, wrap=wrap)
        if next_pane is not None:
            self._request_focus(next_pane)

    def cmd_prev_tab(self, *, wrap: bool = True):
        if self._tree.is_empty:
            return

        next_pane = self._tree.prev_tab(self.focused_pane, wrap=wrap)
        if next_pane is not None:
            self._request_focus(next_pane)

    def cmd_resize_x(self, amount: int = 5):
        if self._tree.is_empty:
            return

        self._tree.resize(self.focused_pane, Axis.x, amount)
        self._request_relayout()

    def cmd_resize_y(self, amount: int = 5):
        if self._tree.is_empty:
            return

        self._tree.resize(self.focused_pane, Axis.y, amount)
        self._request_relayout()

    def cmd_rename_tab(self, widget: str = "prompt"):
        prompt_widget = self.group.qtile.widgets_map.get(widget)
        if prompt_widget is None:
            logger.error(f"The '{widget}' widget was not found")
            return

        prompt_widget.start_input("Rename tab: ", self._handle_rename_tab)

    def cmd_info(self):
        return {
            "name": "bonsai",
            "tree": repr(self._tree),
        }

    def _handle_default_next_window(self) -> BonsaiPane:
        return self._tree.tab()

    def _reset(self):
        # We initialize the tree with arbitrary dimensions. These get reset soon as this
        # layout's group is assigned to a screen.
        self._tree = BonsaiTree(100, 100)
        self._parse_config()

        self._tree.subscribe(
            TreeEvent.node_added, lambda nodes: self._handle_added_tree_nodes(nodes)
        )
        self._tree.subscribe(
            TreeEvent.node_removed, lambda nodes: self._handle_removed_tree_nodes(nodes)
        )

        self._windows_to_panes = {}

        def _handle_next_window():
            return self._tree.tab()

        self._on_next_window = _handle_next_window

    def _parse_config(self):
        config = itertools.chain(
            ((c[0], c[1]) for c in self.defaults),
            ((k, v) for k, v in self._user_config.items()),
        )
        for [key, value] in config:
            level_specific_key = self.level_specific_config_format.match(key)
            level = None
            if level_specific_key is not None:
                level = int(level_specific_key.group(1))
                key = level_specific_key.group(2)
            self._tree.set_config(key, value, level=level)

    def _handle_added_tree_nodes(self, nodes: list[BonsaiNodeMixin]):
        for node in nodes:
            node.init_ui(self.group.qtile)

    def _handle_removed_tree_nodes(self, nodes: list[BonsaiNodeMixin]):
        for node in nodes:
            node.finalize()

    def _handle_rename_tab(self, new_title: str):
        tab = self.focused_pane.get_first_ancestor(Tab)
        tab.title = new_title
        self._request_relayout()

    def _hide_all_internal_windows(self):
        for node in self._tree.iter_walk():
            node.hide()

    def _request_focus(self, pane: BonsaiPane):
        self.group.focus(pane.window)

    def _request_relayout(self):
        self.group.layout_all()
