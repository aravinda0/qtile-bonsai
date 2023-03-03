# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


from typing import Callable

from libqtile.backend.base import Drawer, Internal, Window
from libqtile.config import ScreenRect
from libqtile.core.manager import Qtile
from libqtile.drawer import TextLayout
from libqtile.layout.base import Layout
from libqtile.log_utils import logger

from qtile_bonsai.colors import Gruvbox
from qtile_bonsai.core.geometry import Rect
from qtile_bonsai.core.tree import (
    Axis,
    Pane,
    SplitContainer,
    Tab,
    TabContainer,
    Tree,
    TreeEvent,
)


class BonsaiNodeMixin:
    """A mixin that formalizes UI operations for nodes."""

    def init_ui(self, qtile: Qtile):
        """Handles any initialization of UI elements that are part of this node's
        representation.
        """
        pass

    def load_config(self, layout: "Bonsai"):
        """Reads relevant user configuration and applies it to node state.

        This is something that may not be possible in __init__ as the node's level in
        the tree is only clear post-init when `node.parent` gets set.
        """
        pass

    def render(self, screen_rect: ScreenRect, layout: "Bonsai"):
        """Renders UI elements of this node.

        The `layout` is accepted as a parameter since qtile stores user-passed config
        directly on the `Layout` instance as attributes. The builtin qtile-layouts also
        pass around the entire layout to access user-config.
        """
        pass

    def hide(self):
        """Hides any UI elements of this node."""
        pass

    def finalize(self):
        """Performs any cleanup that may be needed, such as releasing UI resources."""
        pass


class BonsaiTabContainer(BonsaiNodeMixin, TabContainer):
    def __init__(self):
        super().__init__()

        self.bar_window: Internal
        self.bar_drawer: Drawer
        self.bar_text_layout: TextLayout

    def init_ui(self, qtile: Qtile):
        # Arbitrary coords on init. Will get rendered to proper screen position
        # during layout phase.
        self.bar_window = qtile.core.create_internal(0, 0, 1, 1)

        self.bar_drawer = self.bar_window.create_drawer(1, 1)
        self.bar_text_layout = self.bar_drawer.textlayout(
            "", "000000", "mono", 15, None
        )

    def load_config(self, layout: "Bonsai"):
        tab_bar = self.tab_bar
        tab_bar.box.margin = layout.get_config("tab_bar.margin", self.tab_level)
        tab_bar.box.border = layout.get_config("tab_bar.border_size", self.tab_level)

    def render(self, screen_rect: ScreenRect, layout: "Bonsai"):
        level = self.tab_level

        tab_bar_border_color = layout.get_config("tab_bar.border_color", level)
        tab_bar_bg_color = layout.get_config("tab_bar.bg_color", level)

        tab_min_width = layout.get_config("tab_bar.tab.min_width", level)
        layout.get_config("tab_bar.tab.margin", level)  # TODO: use
        layout.get_config("tab_bar.tab.border_color", level)  # TODO: use
        tab_padding = layout.get_config("tab_bar.tab.padding", level)
        tab_font_family = layout.get_config("tab_bar.tab.font_family", level)
        tab_font_size = layout.get_config("tab_bar.tab.font_size", level)
        tab_bg_color = layout.get_config("tab_bar.tab.bg_color", level)
        tab_fg_color = layout.get_config("tab_bar.tab.fg_color", level)

        tab_active_bg_color = layout.get_config("tab_bar.tab.active.bg_color", level)
        tab_active_fg_color = layout.get_config("tab_bar.tab.active.fg_color", level)

        rect = self.tab_bar.box.principal_rect
        self.bar_window.place(
            rect.x,
            rect.y,
            rect.w,
            rect.h,
            borderwidth=self.tab_bar.box.border,
            bordercolor=tab_bar_border_color,
            margin=self.tab_bar.box.margin,
        )
        self.bar_window.unhide()

        self.bar_drawer.width = rect.w
        self.bar_drawer.height = rect.h
        self.bar_drawer.clear(tab_bar_bg_color)

        offset = 0
        for tab in self.children:
            if tab is self.active_child:
                self.bar_drawer.set_source_rgb(tab_active_bg_color)
                self.bar_text_layout.colour = tab_active_fg_color
            else:
                self.bar_drawer.set_source_rgb(tab_bg_color)
                self.bar_text_layout.colour = tab_fg_color

            w, _ = self.bar_drawer.max_layout_size(
                [tab.title], tab_font_family, tab_font_size
            )
            w = max(w + tab_padding * 2, tab_min_width)
            self.bar_drawer.fillrect(offset, 0, w, rect.h)
            self.bar_text_layout.text = tab.title
            self.bar_text_layout.draw(offset + tab_padding, 0)
            offset += w

        self.bar_drawer.draw(0, 0, rect.w, rect.h)

    def hide(self):
        self.bar_window.hide()

    def finalize(self):
        self.bar_text_layout.finalize()
        self.bar_drawer.finalize()
        self.bar_window.kill()


class BonsaiTab(BonsaiNodeMixin, Tab):
    pass


class BonsaiSplitContainer(BonsaiNodeMixin, SplitContainer):
    pass


class BonsaiPane(BonsaiNodeMixin, Pane):
    def __init__(
        self,
        *,
        content_rect: Rect | None = None,
        principal_rect: Rect | None = None,
        margin: int = 0,
        border: int = 1,
    ):
        super().__init__(
            content_rect=content_rect,
            principal_rect=principal_rect,
            margin=margin,
            border=border,
            padding=0,
        )

        self.window: Window

    def load_config(self, layout: "Bonsai"):
        self.box.margin = layout.get_config("window.margin", self.tab_level)
        self.box.border = layout.get_config("window.border_size", self.tab_level)

    def render(self, screen_rect: ScreenRect, layout: "Bonsai"):
        level = self.tab_level

        window_border_color = layout.get_config("window.border_color", level)

        # Use principal rect as qtile windows start with provided x/y/w/h and adjust
        # internally to account for border, margin.
        rect = self.box.principal_rect
        self.window.place(
            rect.x,
            rect.y,
            rect.w,
            rect.h,
            borderwidth=self.box.border,
            bordercolor=window_border_color,
            margin=self.box.margin,
        )
        self.window.unhide()

    def hide(self):
        self.window.hide()


class BonsaiTree(Tree):
    def create_pane(
        self,
        *,
        content_rect: Rect | None = None,
        principal_rect: Rect | None = None,
        margin: int = 0,
        border: int = 1,
    ) -> BonsaiPane:
        return BonsaiPane(
            content_rect=content_rect,
            principal_rect=principal_rect,
            margin=margin,
            border=border,
        )

    def create_split_container(self) -> BonsaiSplitContainer:
        return BonsaiSplitContainer()

    def create_tab(self, title) -> BonsaiTab:
        return BonsaiTab(title)

    def create_tab_container(self) -> BonsaiTabContainer:
        return BonsaiTabContainer()


class Bonsai(Layout):
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
            Gruvbox.dark_yellow,
            "Color of the border around windows",
        ),
        (
            "window.active.border_color",
            Gruvbox.bright_yellow,
            "Color of the border around an active window",
        ),
        (
            "tab_bar.margin",
            0,
            "Size of the margin space around tab bars",
        ),
        (
            "tab_bar.border_size",
            1,
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
        ("tab_bar.tab.border_size", 1, "Size of the border around individual tabs"),
        (
            "tab_bar.tab.border_color",
            Gruvbox.dark_yellow,
            "Color of the border around individual tabs",
        ),
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
                node.render(screen_rect, self)
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

    def get_config(self, key: str, level: int = 1):
        level_key = f"L{level}.{key}"
        if not hasattr(self, level_key):
            level_key = key

        return getattr(self, level_key)

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

    def _handle_added_tree_nodes(self, nodes: list[BonsaiNodeMixin]):
        for node in nodes:
            node.init_ui(self.group.qtile)
            node.load_config(self)

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
