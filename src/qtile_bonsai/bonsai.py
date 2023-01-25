# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


import collections
from typing import Callable

from bidict import bidict
from libqtile import qtile
from libqtile.backend.base import Window
from libqtile.config import ScreenRect
from libqtile.layout.base import Layout
from libqtile.log_utils import logger

from qtile_bonsai.tree import Axis, Node, Pane, TabContainer, Tree, TreeEvent

UITabBar = collections.namedtuple("UITabBar", ["window", "drawer", "text_layout"])


class Bonsai(Layout):
    def __init__(self) -> None:
        super().__init__()

        self._tree: Tree
        self._focused_window: Window
        self._windows_to_panes: bidict[Window, Pane]
        self._on_next_window: Callable[[], Pane]
        self._tab_bars_ui: dict[int, UITabBar] = {}

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
        the layout, then each Group instance 'clones' that original instance (which
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
            if isinstance(node, TabContainer):
                self._layout_tab_container_node(node, screen_rect)
            elif isinstance(node, Pane):
                self._layout_pane_node(node, screen_rect)

    def configure(self, window: Window, screen_rect: ScreenRect):
        """Defined since this is an abstract method, but not implemented since things
        are handled in `self.layout()`.
        """
        raise NotImplementedError

    def add(self, window: Window):
        if self._tree.is_empty:
            self._on_next_window = self._handle_default_next_window

        pane = self._on_next_window()
        self._windows_to_panes[window] = pane

    def remove(self, window: Window):
        pane = self._windows_to_panes[window]
        next_focus_pane = self._tree.remove(pane)
        del self._windows_to_panes[window]
        if next_focus_pane is not None:
            return self._windows_to_panes.inv[next_focus_pane]

    def focus(self, window: Window):
        self._focused_window = window
        self._tree.focus(self.focused_pane)

    def focus_first(self):
        pass

    def focus_last(self):
        pass

    def focus_next(self, window):
        pass

    def focus_previous(self, window):
        pass

    def cmd_next(self):
        pass

    def cmd_previous(self):
        pass

    def hide(self):
        # While other layouts are active, ensure that any new windows are captured
        # consistenty with the default tab layout here.
        self._on_next_window = self._handle_default_next_window

        self._hide_all_internal_windows()

    def cmd_spawn_split(self, program: str, axis: Axis, ratio: float = 0.5):
        if self._tree.is_empty:
            logger.warn("There are no windows yet to split")
            return

        def _handle_next_window():
            return self._tree.split(self.focused_pane, axis, ratio)

        self._on_next_window = _handle_next_window

        qtile.cmd_spawn(program)

    def cmd_spawn_tab(
        self, program: str, new_level: bool = False, level: int | None = None
    ):
        def _handle_next_window():
            return self._tree.add_tab(
                self.focused_pane, new_level=new_level, level=level
            )

        self._on_next_window = _handle_next_window

        qtile.cmd_spawn(program)

    def cmd_left(self, wrap=True):
        if self._tree.is_empty:
            return

        next_pane = self._tree.left(self.focused_pane, wrap=wrap)
        self._request_focus(next_pane)

    def cmd_right(self, wrap=True):
        if self._tree.is_empty:
            return

        next_pane = self._tree.right(self.focused_pane, wrap=wrap)
        self._request_focus(next_pane)

    def cmd_up(self, wrap=True):
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

    def cmd_resize_x(self, amount: float = 0.05):
        if self._tree.is_empty:
            return

        self._tree.resize(self.focused_pane, Axis.x, amount)
        self._request_relayout()

    def cmd_resize_y(self, amount: float = 0.05):
        if self._tree.is_empty:
            return

        self._tree.resize(self.focused_pane, Axis.y, amount)
        self._request_relayout()

    def _handle_default_next_window(self):
        return self._tree.add_tab()

    def _reset(self):
        self._tree = Tree()
        self._tree.subscribe(
            TreeEvent.node_added, lambda nodes: self._handle_added_tree_nodes(nodes)
        )
        self._tree.subscribe(
            TreeEvent.node_removed, lambda nodes: self._handle_removed_tree_nodes(nodes)
        )

        self._windows_to_panes = bidict()
        self._tab_bars_ui = {}

        def _handle_next_window():
            return self._tree.add_tab()

        self._on_next_window = _handle_next_window

    def _handle_added_tree_nodes(self, nodes: list[Node]):
        for node in nodes:
            if isinstance(node, TabContainer):
                # Arbitrary coords on init. Will get rendered to proper screen position
                # during layout phase.
                tab_bar = self.group.qtile.core.create_internal(0, 0, 1, 1)
                drawer = tab_bar.create_drawer(1, 1)
                text_layout = drawer.textlayout("", "000000", "mono", 15, None)
                self._tab_bars_ui[node.id] = UITabBar(tab_bar, drawer, text_layout)

    def _handle_removed_tree_nodes(self, nodes: list[Node]):
        for node in nodes:
            if isinstance(node, TabContainer):
                tab_bar_ui = self._tab_bars_ui[node.id]
                tab_bar_ui.text_layout.finalize()
                tab_bar_ui.drawer.finalize()
                tab_bar_ui.window.kill()
                del self._tab_bars_ui[node.id]

    def _layout_tab_container_node(
        self, tab_container: TabContainer, screen_rect: ScreenRect
    ):
        tab_bar_ui = self._tab_bars_ui[tab_container.id]
        if self._tree.is_visible(tab_container):
            r = tab_container.tab_bar.rect.to_screen_space(screen_rect)

            tab_bar_ui.window.place(r.x, r.y, r.width, r.height, 1, "#0000ff")
            tab_bar_ui.window.unhide()

            tab_bar_ui.drawer.width = r.width
            tab_bar_ui.drawer.height = r.height
            tab_bar_ui.drawer.clear("00ffff")

            for i, tab in enumerate(tab_container.children):
                if tab is tab_container.active_child:
                    tab_bar_ui.drawer.set_source_rgb("ff0000")
                    tab_bar_ui.text_layout.colour = "0000ff"
                else:
                    tab_bar_ui.drawer.set_source_rgb("0000ff")
                    tab_bar_ui.text_layout.colour = "00ff00"
                tab_bar_ui.drawer.fillrect(i * 100, 0, 100, r.height)
                tab_bar_ui.text_layout.text = tab.title or "my tab"
                tab_bar_ui.text_layout.draw(i * 100, 0)

            tab_bar_ui.drawer.draw(0, 0, r.width, r.height)
        else:
            tab_bar_ui.window.hide()

    def _layout_pane_node(self, pane: Pane, screen_rect: ScreenRect):
        window = self._windows_to_panes.inv[pane]
        if self._tree.is_visible(pane):
            r = pane.rect.to_screen_space(screen_rect)
            window.place(r.x, r.y, r.width, r.height, 1, "#ff0000")
            window.unhide()
        else:
            window.hide()

    def _hide_all_internal_windows(self):
        for tab_bar_ui in self._tab_bars_ui.values():
            tab_bar_ui.window.hide()

    def _request_focus(self, pane: Pane):
        window = self._windows_to_panes.inv[pane]
        self.group.focus(window)

    def _request_relayout(self):
        self.group.layout_all()
