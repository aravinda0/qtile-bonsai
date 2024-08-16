# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT

from collections.abc import Callable

from libqtile.backend.base.drawer import Drawer, TextLayout
from libqtile.backend.base.window import Internal, Window
from libqtile.config import ScreenRect
from libqtile.core.manager import Qtile
from libqtile.group import _Group

from qtile_bonsai.core.geometry import Box, Perimeter, PerimieterParams, Rect
from qtile_bonsai.core.nodes import Node, Pane, SplitContainer, Tab, TabContainer
from qtile_bonsai.core.tree import Tree


class BonsaiNodeMixin:
    """A mixin that formalizes UI operations for nodes."""

    def init_ui(self, qtile: Qtile):
        """Handles any initialization of UI elements that are part of this node's
        representation.

        TODO: Review. This approach may no longer be necessary after some changes where
        `group.qtile` is now passed to `BonsaiTree`.
        """
        pass

    def render(self, screen_rect: ScreenRect):
        """Renders UI elements of this node."""
        pass

    def hide(self):
        """Hides any UI elements of this node."""
        pass

    def finalize(self):
        """Performs any cleanup that may be needed, such as releasing UI resources."""
        pass


class BonsaiTabContainer(BonsaiNodeMixin, TabContainer):
    TabBarClickHandler = Callable[["BonsaiTabContainer", int, int], None]

    def __init__(
        self,
        tree: "BonsaiTree",
        on_click_tab_bar: "BonsaiTabContainer.TabBarClickHandler | None" = None,
    ):
        super().__init__()

        self.bar_window: Internal
        self.bar_drawer: Drawer
        self.bar_text_layout: TextLayout

        self._tree = tree
        self._on_click_tab_bar: "BonsaiTabContainer.TabBarClickHandler | None" = (
            on_click_tab_bar
        )

    def init_ui(self, qtile: Qtile):
        # Arbitrary coords on init. Will get rendered to proper screen position
        # during layout phase.
        self.bar_window = qtile.core.create_internal(0, 0, 1, 1)
        self.bar_window.process_button_click = self._handle_click_bar

        self.bar_drawer = self.bar_window.create_drawer(1, 1)
        self.bar_text_layout = self.bar_drawer.textlayout(
            "", "000000", "mono", 15, None
        )

    def render(self, screen_rect: ScreenRect):
        if self.tab_bar.is_hidden:
            self.hide()
            return

        tree = self._tree
        level = self.tab_level

        tab_bar_border_color: str = tree.get_config("tab_bar.border_color", level=level)
        tab_bar_bg_color: str = tree.get_config("tab_bar.bg_color", level=level)

        tab_margin = Perimeter(tree.get_config("tab_bar.tab.margin", level=level))
        tab_padding = Perimeter(tree.get_config("tab_bar.tab.padding", level=level))
        tab_font_family: str = tree.get_config("tab_bar.tab.font_family", level=level)
        tab_font_size: float = tree.get_config("tab_bar.tab.font_size", level=level)
        tab_bg_color: str = tree.get_config("tab_bar.tab.bg_color", level=level)
        tab_fg_color: str = tree.get_config("tab_bar.tab.fg_color", level=level)

        tab_active_bg_color: str = tree.get_config(
            "tab_bar.tab.active.bg_color", level=level
        )
        tab_active_fg_color: str = tree.get_config(
            "tab_bar.tab.active.fg_color", level=level
        )

        place_window_using_box(
            self.bar_window, self.tab_bar.box, tab_bar_border_color, screen_rect
        )
        self.bar_window.unhide()

        bar_rect = self.tab_bar.box.principal_rect

        self.bar_drawer.width = bar_rect.w
        self.bar_drawer.height = bar_rect.h

        # NOTE: This hack is a workaround after some changes in qtile 0.23 under X. When
        # the drawer surface width expands, the xcb surface is freed, but not
        # re-created. No problem under Wayland.
        # Re-creation only happens later when `drawer._check_xcb()` is invoked in
        # `drawer.draw()`. But that check doesn't happen in `drawer.clear()`, and
        # that's when we face an exception.
        if hasattr(self.bar_drawer, "_check_xcb"):
            self.bar_drawer._check_xcb()

        self.bar_drawer.clear(tab_bar_bg_color)

        per_tab_w = self._get_per_tab_width()

        # NOTE: This is accurate for monospaced fonts, but is still a safe enough
        # approximation for non-monospaced fonts as we may only over-estimate.
        one_char_w, _ = self.bar_drawer.max_layout_size(
            ["x"], tab_font_family, tab_font_size
        )
        per_tab_max_chars = int(
            (
                per_tab_w
                - (tab_margin.left + tab_margin.right)
                - (tab_padding.left + tab_padding.right)
            )
            / one_char_w
        )

        for i, tab in enumerate(self.children):
            if tab is self.active_child:
                self.bar_drawer.set_source_rgb(tab_active_bg_color)
                self.bar_text_layout.colour = tab_active_fg_color
            else:
                self.bar_drawer.set_source_rgb(tab_bg_color)
                self.bar_text_layout.colour = tab_fg_color
            self.bar_text_layout.font_family = tab_font_family
            self.bar_text_layout.font_size = tab_font_size

            tab_box = self._get_object_space_tab_box(i, per_tab_w)

            # Truncate title based on available width
            tab_title = tab.title_resolved
            if len(tab_title) > per_tab_max_chars:
                tab_title = f"{tab_title[:per_tab_max_chars - 1]}…"

            # Draw the tab
            self.bar_drawer.fillrect(
                tab_box.border_rect.x,
                tab_box.border_rect.y,
                tab_box.border_rect.w,
                tab_box.border_rect.h,
            )

            # Center title text in the tab and draw it
            text_w, text_h = self.bar_drawer.max_layout_size(
                [tab_title], tab_font_family, tab_font_size
            )
            self.bar_text_layout.text = tab_title
            text_offset_x = (tab_box.content_rect.w - text_w) / 2
            text_offset_y = (tab_box.content_rect.h - text_h) / 2
            self.bar_text_layout.draw(
                tab_box.content_rect.x + text_offset_x,
                tab_box.content_rect.y + text_offset_y,
            )

        self.bar_drawer.draw(0, 0, bar_rect.w, bar_rect.h)

    def hide(self):
        self.bar_window.hide()

    def finalize(self):
        self.bar_text_layout.finalize()
        self.bar_drawer.finalize()
        self.bar_window.kill()

    def as_dict(self) -> dict:
        state = super().as_dict()
        state["tab_bar"]["is_window_visible"] = self.bar_window.is_visible()
        return state

    def _handle_click_bar(self, x: int, y: int, button: int):
        if self._on_click_tab_bar is None:
            return

        per_tab_w = self._get_per_tab_width()
        i = x // per_tab_w

        if i > len(self.children) - 1:
            return

        tab_box = self._get_object_space_tab_box(i, per_tab_w)

        # Note that the `x`, `y` provided here by qtile are object space coords.
        if tab_box.border_rect.has_coord(x, y):
            self._on_click_tab_bar(self, i, button)

    def _get_per_tab_width(self) -> int:
        tab_width_config: int | str = self._tree.get_config("tab_bar.tab.width")
        if tab_width_config == "auto":
            return self.tab_bar.box.principal_rect.w // len(self.children)
        return int(tab_width_config)

    def _get_object_space_tab_box(self, i: int, per_tab_w: int) -> Box:
        bar_rect = self.tab_bar.box.principal_rect
        return Box(
            principal_rect=Rect((i * per_tab_w), 0, per_tab_w, bar_rect.h),
            margin=self._tree.get_config("tab_bar.tab.margin", level=self.tab_level),
            border=0,
            padding=self._tree.get_config("tab_bar.tab.padding", level=self.tab_level),
        )


class BonsaiTab(BonsaiNodeMixin, Tab):
    def __init__(
        self,
        title: str,
        tree: "BonsaiTree",
    ):
        super().__init__(title)

        self._tree = tree

    @property
    def title_resolved(self) -> str:
        tab_title_provider: Callable[[int, BonsaiPane, BonsaiTab], str] | None = (
            self._tree.get_config("tab_bar.tab.title_provider", level=self.tab_level)
        )

        i = self.parent.children.index(self)
        if tab_title_provider is not None:
            active_pane = self._tree.find_mru_pane(start_node=self)
            if active_pane.window is not None:
                return tab_title_provider(i, active_pane, self)

        return f"{i + 1}: {self.title}" if self.title else f"{i + 1}"

    def as_dict(self) -> dict:
        state = super().as_dict()
        state["title_resolved"] = self.title_resolved
        return state


class BonsaiSplitContainer(BonsaiNodeMixin, SplitContainer):
    pass


class BonsaiPane(BonsaiNodeMixin, Pane):
    def __init__(
        self,
        principal_rect: Rect | None = None,
        *,
        margin: PerimieterParams = 0,
        border: PerimieterParams = 1,
        tree: "BonsaiTree",
    ):
        super().__init__(
            principal_rect=principal_rect,
            margin=margin,
            border=border,
            padding=0,
        )

        self.window: Window | None = None

        self._tree = tree  # just for config

    def render(self, screen_rect: ScreenRect):
        if self.window is None:
            return

        if self.window.has_focus:
            window_border_color = self._tree.get_config(
                "window.active.border_color", level=self.tab_level
            )
        else:
            window_border_color = self._tree.get_config(
                "window.border_color", level=self.tab_level
            )

        place_window_using_box(self.window, self.box, window_border_color, screen_rect)
        self.window.unhide()

    def hide(self):
        if self.window is None:
            return

        self.window.hide()

    def as_dict(self) -> dict:
        state = super().as_dict()
        state["wid"] = self.window.wid if self.window is not None else None
        state["is_window_visible"] = (
            self.window.is_visible() if self.window is not None else None
        )
        return state


class BonsaiTree(Tree):
    def __init__(
        self,
        width: int,
        height: int,
        group: _Group,
        config: Tree.MultiLevelConfig | None = None,
        on_click_tab_bar: BonsaiTabContainer.TabBarClickHandler | None = None,
    ):
        super().__init__(width, height, config)

        # Invariant: A layout instance's linked group does not change.
        self._group = group

        self._container_selection: ContainerSelection = ContainerSelection(
            self, group.qtile
        )
        self._on_click_tab_bar = on_click_tab_bar

    @property
    def selected_node(self) -> Node | None:
        return self._container_selection.focused_node

    def create_pane(
        self,
        principal_rect: Rect | None = None,
        *,
        margin: PerimieterParams | None = None,
        border: PerimieterParams | None = None,
        tab_level: int | None = None,
    ) -> BonsaiPane:
        if margin is None:
            margin = self.get_config("window.margin", level=tab_level)
        if border is None:
            border = self.get_config("window.border_size", level=tab_level)

        return BonsaiPane(
            principal_rect=principal_rect,
            margin=margin,
            border=border,
            tree=self,
        )

    def create_split_container(self) -> BonsaiSplitContainer:
        return BonsaiSplitContainer()

    def create_tab(self, title: str = "") -> BonsaiTab:
        return BonsaiTab(title, tree=self)

    def create_tab_container(self) -> BonsaiTabContainer:
        return BonsaiTabContainer(tree=self, on_click_tab_bar=self._on_click_tab_bar)

    def render(self, screen_rect: ScreenRect):
        for node in self.iter_walk():
            if self.is_visible(node):
                node.render(screen_rect)
            else:
                node.hide()
        self._container_selection.render(screen_rect)

    def finalize(self):
        self._container_selection.finalize()
        for node in self.iter_walk():
            node.finalize()

    def hide(self):
        for node in self.iter_walk():
            node.hide()

    def activate_selection(self, node: Node):
        self._container_selection.focused_node = node

    def clear_selection(self):
        self._container_selection.focused_node = None

    def handle_bar_hiding_config(self, tc: BonsaiTabContainer):
        """ """
        if (
            tc.tab_level == 1
            and not self.is_empty
            and self.get_config("tab_bar.hide_L1_when_bonsai_bar_on_screen")
        ):
            bonsai_widgets_on_same_screen = [
                w
                for (wname, w) in self._group.qtile.widgets_map.items()
                # qtile will rename keys if there are multiple of the same widget kind
                # at play
                if wname.partition("_")[0] == "bonsaibar"
                and w.bar.screen is self._group.screen
            ]
            if bonsai_widgets_on_same_screen:
                tc.collapse_tab_bar()
                return

        super().handle_bar_hiding_config(tc)


class ContainerSelection:
    """Manages a UI rect representing a 'selection' of a BonsaiNode subtree in the form
    of a border around them.

    The border is implemented in a somewhat quirky way as a collection of 4 thin windows
    positioned around the selection target. This helps to make things work with basic X
    windows without transparency providers such as picom (where we could simply have one
    overlay window and give it a border while making its body transparent).
    """

    def __init__(self, tree: BonsaiTree, qtile: Qtile):
        self.focused_node: Node | None = None

        self._tree = tree  # just to be able to access config

        self._win_t = qtile.core.create_internal(0, 0, 1, 1)
        self._win_r = qtile.core.create_internal(0, 0, 1, 1)
        self._win_b = qtile.core.create_internal(0, 0, 1, 1)
        self._win_l = qtile.core.create_internal(0, 0, 1, 1)

        self._drawer_t = self._win_t.create_drawer(1, 1)
        self._drawer_r = self._win_r.create_drawer(1, 1)
        self._drawer_b = self._win_b.create_drawer(1, 1)
        self._drawer_l = self._win_l.create_drawer(1, 1)

    def render(self, screen_rect: ScreenRect):
        if self.focused_node is None:
            self._win_t.hide()
            self._win_r.hide()
            self._win_b.hide()
            self._win_l.hide()
            return

        border_size: int = self._tree.get_config("container_select_mode.border_size")
        border_color: str = self._tree.get_config("container_select_mode.border_color")

        rect = self.focused_node.principal_rect
        is_x = hasattr(self._drawer_t, "_check_xcb")  # See notes in BonsaiTabContainer

        rect_t = Rect(rect.x, rect.y, rect.w, border_size)
        place_window_using_box(self._win_t, Box(rect_t), "000000", screen_rect)
        self._win_t.unhide()
        self._win_t.bring_to_front()
        self._drawer_t.width = rect_t.w
        self._drawer_t.height = rect_t.h
        if is_x:
            self._drawer_t._check_xcb()
        self._drawer_t.clear(border_color)
        self._drawer_t.draw(0, 0, rect_t.w, rect_t.h)

        rect_r = Rect(rect.x2 - border_size, rect.y, border_size, rect.h)
        place_window_using_box(self._win_r, Box(rect_r), "000000", screen_rect)
        self._win_r.unhide()
        self._win_r.bring_to_front()
        self._drawer_r.width = rect_r.w
        self._drawer_r.height = rect_r.h
        if is_x:
            self._drawer_r._check_xcb()
        self._drawer_r.clear(border_color)
        self._drawer_r.draw(0, 0, rect_r.w, rect_r.h)

        rect_b = Rect(rect.x, rect.y2 - border_size, rect.w, border_size)
        place_window_using_box(self._win_b, Box(rect_b), "000000", screen_rect)
        self._win_b.unhide()
        self._win_b.bring_to_front()
        self._drawer_b.width = rect_b.w
        self._drawer_b.height = rect_b.h
        if is_x:
            self._drawer_b._check_xcb()
        self._drawer_b.clear(border_color)
        self._drawer_b.draw(0, 0, rect_b.w, rect_b.h)

        rect_l = Rect(rect.x, rect.y, border_size, rect.h)
        place_window_using_box(self._win_l, Box(rect_l), "000000", screen_rect)
        self._win_l.unhide()
        self._win_l.bring_to_front()
        self._drawer_l.width = rect_l.w
        self._drawer_l.height = rect_l.h
        if is_x:
            self._drawer_l._check_xcb()
        self._drawer_l.clear(border_color)
        self._drawer_l.draw(0, 0, rect_l.w, rect_l.h)

    def finalize(self):
        self._drawer_t.finalize()
        self._drawer_r.finalize()
        self._drawer_b.finalize()
        self._drawer_l.finalize()

        self._win_t.kill()
        self._win_r.kill()
        self._win_b.kill()
        self._win_l.kill()


def place_window_using_box(
    window: Window | Internal, box: Box, border_color: str, screen_rect: ScreenRect
):
    """Invokes window.place on qtile window instances, translating coordinates from a
    Box instance.

    qtile window x/y coordinates include borders, but their width/height are those of
    the content excluding borders. Margins are processed separately and enclose the
    provided x/y coords.
    """
    border_rect = box.border_rect
    content_rect = box.content_rect

    # qtile windows only support single valued border that is applied on all sides
    border = box.border.top

    window.place(
        border_rect.x + screen_rect.x,
        border_rect.y + screen_rect.y,
        content_rect.w,
        content_rect.h,
        borderwidth=border,
        bordercolor=border_color,
        margin=box.margin.as_list(),
    )
