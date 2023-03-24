# SPDX-FileCopyrightText: 2023-present Aravinda Rao <maniacalace@gmail.com>
# SPDX-License-Identifier: MIT


from libqtile.backend.base import Drawer, Internal, Window
from libqtile.config import ScreenRect
from libqtile.core.manager import Qtile
from libqtile.drawer import TextLayout

from qtile_bonsai.core.geometry import Box, Rect
from qtile_bonsai.core.tree import (
    Pane,
    SplitContainer,
    Tab,
    TabContainer,
    Tree,
)


class BonsaiNodeMixin:
    """A mixin that formalizes UI operations for nodes."""

    def init_ui(self, qtile: Qtile):
        """Handles any initialization of UI elements that are part of this node's
        representation.
        """
        pass

    def render(self, screen_rect: ScreenRect, tree: "BonsaiTree"):
        """Renders UI elements of this node."""
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

    def render(self, screen_rect: ScreenRect, tree: "BonsaiTree"):
        if self.tab_bar.is_hidden:
            return

        level = self.tab_level

        tab_bar_border_color = tree.get_config("tab_bar.border_color", for_level=level)
        tab_bar_bg_color = tree.get_config("tab_bar.bg_color", for_level=level)

        tab_min_width = tree.get_config("tab_bar.tab.min_width", for_level=level)
        tab_margin = tree.get_config("tab_bar.tab.margin", for_level=level)
        tab_padding = tree.get_config("tab_bar.tab.padding", for_level=level)
        tab_font_family = tree.get_config("tab_bar.tab.font_family", for_level=level)
        tab_font_size = tree.get_config("tab_bar.tab.font_size", for_level=level)
        tab_bg_color = tree.get_config("tab_bar.tab.bg_color", for_level=level)
        tab_fg_color = tree.get_config("tab_bar.tab.fg_color", for_level=level)

        tab_active_bg_color = tree.get_config(
            "tab_bar.tab.active.bg_color", for_level=level
        )
        tab_active_fg_color = tree.get_config(
            "tab_bar.tab.active.fg_color", for_level=level
        )

        place_window_using_box(
            self.bar_window, self.tab_bar.box, tab_bar_border_color, screen_rect
        )
        self.bar_window.unhide()

        bar_rect = self.tab_bar.box.principal_rect

        self.bar_drawer.width = bar_rect.w
        self.bar_drawer.height = bar_rect.h
        self.bar_drawer.clear(tab_bar_bg_color)

        offset = 0
        for i, tab in enumerate(self.children):
            # Prime drawers with colors
            if tab is self.active_child:
                self.bar_drawer.set_source_rgb(tab_active_bg_color)
                self.bar_text_layout.colour = tab_active_fg_color
            else:
                self.bar_drawer.set_source_rgb(tab_bg_color)
                self.bar_text_layout.colour = tab_fg_color

            # Compute space for the tab rect
            tab_title = f"{i + 1}: {tab.title}" if tab.title else f"{i + 1}"
            content_w, _ = self.bar_drawer.max_layout_size(
                [tab_title], tab_font_family, tab_font_size
            )
            principal_w = max(
                tab_min_width, content_w + (2 * tab_margin) + (2 * tab_padding)
            )
            tab_box = Box(
                principal_rect=Rect(offset, 0, principal_w, bar_rect.h),
                margin=tab_margin,
                border=0,  # Individual tabs don't have borders
                padding=tab_padding,
            )

            # Draw the tab
            self.bar_drawer.fillrect(
                tab_box.border_rect.x, 0, tab_box.border_rect.w, bar_rect.h
            )
            self.bar_text_layout.text = tab_title
            self.bar_text_layout.draw(tab_box.content_rect.x, 0)

            offset += principal_w

        self.bar_drawer.draw(0, 0, bar_rect.w, bar_rect.h)

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

    def render(self, screen_rect: ScreenRect, tree: "BonsaiTree"):
        if self.window.has_focus:
            window_border_color = tree.get_config(
                "window.active.border_color", for_level=self.tab_level
            )
        else:
            window_border_color = tree.get_config(
                "window.border_color", for_level=self.tab_level
            )

        place_window_using_box(self.window, self.box, window_border_color, screen_rect)
        self.window.unhide()

    def hide(self):
        self.window.hide()


class BonsaiTree(Tree):
    def create_pane(
        self,
        *,
        principal_rect: Rect | None = None,
        content_rect: Rect | None = None,
        margin: int | None = None,
        border: int | None = None,
        tab_level: int | None = None,
    ) -> BonsaiPane:
        if margin is None:
            margin = self.get_config("window.margin", for_level=tab_level)
        if border is None:
            border = self.get_config("window.border_size", for_level=tab_level)

        return BonsaiPane(
            principal_rect=principal_rect,
            content_rect=content_rect,
            margin=margin,
            border=border,
        )

    def create_split_container(self) -> BonsaiSplitContainer:
        return BonsaiSplitContainer()

    def create_tab(self, title: str = "") -> BonsaiTab:
        return BonsaiTab(title)

    def create_tab_container(self) -> BonsaiTabContainer:
        return BonsaiTabContainer()


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
    window.place(
        border_rect.x + screen_rect.x,
        border_rect.y + screen_rect.y,
        content_rect.w,
        content_rect.h,
        borderwidth=box.border,
        bordercolor=border_color,
        margin=box.margin,
    )
